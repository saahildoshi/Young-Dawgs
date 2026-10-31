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


def test_interrupted_parent_cannot_skip_its_unfinished_loading_target(tmp_path,monkeypatch):
    import json
    import pytest
    import scripts.v066_campaign as campaign
    root=tmp_path/'run';base=tmp_path/'native';(root/'mechanical_results').mkdir(parents=True);(base/'parent').mkdir(parents=True)
    q={'last_state_accepted':True,'results':[{'accepted':True}],'states':[{'time':.00859375,'load_step':2,'substep':7}],'source':str(base/'parent')}
    (root/'mechanical_results/parent_qualification001.json').write_text(json.dumps(q))
    (base/'parent/simulation_manifest.json').write_text(json.dumps({'target_strain':.01}))
    monkeypatch.setattr(campaign,'RUN',root);monkeypatch.setattr(campaign,'BASE',base)
    with pytest.raises(ValueError,match='target is incomplete'):campaign.prepare_next('next','parent',[.05])
    assert not (base/'next').exists()
