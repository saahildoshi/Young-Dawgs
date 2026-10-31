"""A later valid-looking endpoint cannot erase an invalid loading history."""
from scripts.v066_post import trajectory_member


def state(time,accepted=True):
    return {'state':{'time':time,'load_step':1,'substep':int(time*100)},'accepted':accepted,'failures':[] if accepted else ['unmodeled crossing'],'status':'PASS' if accepted else 'HOLD'}


def test_invalid_saved_state_quarantines_later_individually_passing_state():
    first,prior=trajectory_member(state(.01,False),None)
    last,prior=trajectory_member(state(.02),prior)
    assert not last['accepted'] and last['earlier_failed_state']==first['state']
    assert first['failures']==['unmodeled crossing']


def test_valid_prefix_survives_and_stops_exactly_at_first_failure():
    rows=[];prior=None
    for q in [state(.01),state(.02),state(.03,False),state(.04)]:
        item,prior=trajectory_member(q,prior);rows.append(item)
    assert [q['accepted'] for q in rows]==[True,True,False,False]
    assert prior==rows[2]['state']
