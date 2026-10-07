import copy
from dataclasses import fields

import pytest

from risa.core.graph_store import GraphStore
from risa.core.models import Edge, Node
from experiments.references.graph_store_before_20261007 import GraphStore as BeforeGraphStore


def assert_same(left, right):
    assert left.to_dict() == right.to_dict()
    assert left.to_compact_dict() == right.to_compact_dict()
    assert left.adjacency_in == right.adjacency_in
    assert left.adjacency_out == right.adjacency_out
    assert left.metabolism_pending == right.metabolism_pending
    assert left.coactivation_neighbors == right.coactivation_neighbors


@pytest.mark.parametrize('compact', [False, True])
def test_all_graph_fields_and_duplicate_merge_semantics_match_reference(compact):
    nodes = [Node('n', 'entity', '日本語', {'a':'value'}, 2, 3, 4, .5, .6, .7, 8, True),
             Node('other', 'state', '简体中文'),
             Node('n', 'ignored-kind', 'ignored-label', {'b':'new'}, stability=.8)]
    edges = [Edge('n', 'other', 'co_activates_with', ('z','a'), 0, .7, .4, 2),
             Edge('n', 'other', 'co_activates_with', ('b','a'), 3, .9, .8, 5),
             Edge('other', 'n', 'before', (), -2, .3, .2, 1)]
    records = {'nodes':[node.to_dict() for node in nodes], 'edges':[edge.to_dict() for edge in edges]}
    if compact:
        records = {'format':'compact-v1',
                   'nodes': [[getattr(n, f.name) for f in fields(Node)] for n in nodes],
                   'edges': [[getattr(e, f.name) for f in fields(Edge)] for e in edges]}
    snapshot = copy.deepcopy(records)
    reference_records = copy.deepcopy(records)
    actual = GraphStore.from_dict(records)
    expected = BeforeGraphStore.from_dict(reference_records)
    assert_same(actual, expected)
    assert records == reference_records
    if compact:
        assert records == snapshot
    assert actual.get_node('n').usage_count == 5
    assert actual.get_node('n').label == '日本語'
    assert actual.edges_by_key[('n','other','co_activates_with')].evidence_count == 4
    assert actual.edges_by_key[('n','other','co_activates_with')].context_tags == ('a','b','z')
    assert actual.edges_by_key[('n','other','co_activates_with')].reliability == .7
    assert actual.coactivation_neighbors == {'n':{'other'},'other':{'n'}}
    # Mutation and incremental updates after loading keep the same graph behavior.
    actual.add_or_update_edge(Edge('other', 'n', 'before', ('next',), 2, last_updated=8))
    expected.add_or_update_edge(Edge('other', 'n', 'before', ('next',), 2, last_updated=8))
    assert_same(actual, expected)


@pytest.mark.parametrize('kind', ['nodes', 'edges'])
def test_truncated_compact_records_preserve_rejection(kind):
    payload = {'format':'compact-v1', kind:[['too-short']]}
    for cls in (GraphStore, BeforeGraphStore):
        with pytest.raises(IndexError):
            cls.from_dict(payload)


def test_extra_compact_columns_and_attribute_copy_are_preserved():
    source = BeforeGraphStore()
    source.add_or_update_node(Node('n', 'entity', 'label', {'key':'value'}))
    source.add_or_update_edge(Edge('n', 'n', 'before'))
    records = source.to_compact_dict()
    records['nodes'][0].append('future-extra')
    records['edges'][0].append('future-extra')
    actual = GraphStore.from_dict(records)
    assert_same(actual, BeforeGraphStore.from_dict(records))
    actual.get_node('n').attributes['key'] = 'changed'
    assert records['nodes'][0][3]['key'] == 'value'


def test_repeated_context_tags_share_immutable_tuple_and_allow_independent_edge_updates():
    payload = {'nodes':[], 'edges':[
        {'source':'a','target':'b','relation_type':'before','context_tags':['same']},
        {'source':'c','target':'d','relation_type':'before','context_tags':['same']}]}
    actual = GraphStore.from_dict(payload)
    first = actual.edges_by_key[('a','b','before')]
    second = actual.edges_by_key[('c','d','before')]
    assert first.context_tags is second.context_tags
    actual.add_or_update_edge(Edge('a','b','before', ('new',)))
    assert first.context_tags == ('new','same')
    assert second.context_tags == ('same',)
    assert payload['edges'][0]['context_tags'] == ['same']


def test_context_pool_is_bounded_and_preserves_non_string_records():
    from risa.core.graph_store import _restore_context_tags
    pool = {}
    originals = [False, 0, 1.0, None, {'unhashable':'value'}]
    for value in originals:
        assert _restore_context_tags([value], pool)[0] is value
    assert pool == {}
    for i in range(200):
        assert _restore_context_tags([f'tag{i}'], pool) == (f'tag{i}',)
    assert len(pool) == 128
    assert _restore_context_tags(['tag0'], pool) is pool[('tag0',)]
    assert _restore_context_tags(['tag199'], pool) == ('tag199',)


@pytest.mark.parametrize('compact', [False, True])
def test_context_values_accepted_by_previous_graph_loader_remain_unchanged(compact):
    source = BeforeGraphStore()
    for i, tags in enumerate(((True,), (1,), (1.0,), (None,), ({'key':'value'},))):
        source.add_or_update_edge(Edge(str(i), 'target', 'before', tags))
    payload = source.to_compact_dict() if compact else source.to_dict()
    actual = GraphStore.from_dict(payload)
    assert_same(actual, BeforeGraphStore.from_dict(payload))
    assert [type(e.context_tags[0]) for e in actual.edges_by_key.values()] == [bool,int,float,type(None),dict]


def test_string_subclass_context_values_keep_their_original_type():
    from risa.core.graph_store import _restore_context_tags
    class Label(str):
        pass
    pool = {}
    _restore_context_tags(['same'], pool)
    label = Label('same')
    assert _restore_context_tags([label], pool)[0] is label
    _restore_context_tags(['same','other'], pool)
    assert _restore_context_tags([label,'other'], pool)[0] is label
