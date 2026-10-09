from experiments.end_to_end_stability import summarize_runs


def test_stability_preserves_censored_timeouts_and_errors():
    complete={'event_scale':100000,'status':'complete','worker_wall_seconds':30,
              'prediction_correct':12,'query_count':12,'prediction_mismatches_after_reload':0,
              'prediction_mismatches_after_compaction':0}
    timeout={'event_scale':100000,'status':'time_budget_exceeded','worker_wall_seconds':45,
             'ingested_events':90000}
    error={'event_scale':100000,'status':'error','worker_wall_seconds':2}
    row=summarize_runs([{'rows':[complete]},{'rows':[timeout]},{'rows':[error]}])[0]
    assert (row['attempts'],row['completed'],row['timeouts'],row['errors'])==(3,1,1,1)
    assert row['completed_worker_wall_median_seconds']==30
    assert row['completed_worker_wall_max_seconds']==30
    assert row['correct_predictions']==row['queries']==12


def test_stability_keeps_failed_correctness_and_no_completion():
    runs=[{'rows':[{'event_scale':1000,'status':'complete','worker_wall_seconds':1,
                   'prediction_correct':11,'query_count':12,'prediction_mismatches_after_reload':1,
                   'prediction_mismatches_after_compaction':2},
                  {'event_scale':100000,'status':'time_budget_exceeded','worker_wall_seconds':45}]}]
    small,large=summarize_runs(runs)
    assert small['correct_predictions']==11
    assert small['reload_mismatches']==1 and small['compaction_mismatches']==2
    assert large['completed_worker_wall_median_seconds'] is None
    assert large['completed_worker_wall_p99_seconds'] is None
