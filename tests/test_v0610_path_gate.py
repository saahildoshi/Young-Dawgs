"""A new material branch may use only a continuous independently accepted onset proof."""
from scripts.v0610_polymer import qualified_onset_prefix


def test_complete_accepted_onset_prefix_can_precede_a_rejected_higher_diagnostic():
    q={'states':[{'accepted':True,'requested_time':.005},{'accepted':True,'requested_time':.012675},{'accepted':False,'requested_time':.015}]}
    assert qualified_onset_prefix(q)==.012675


def test_late_passing_state_cannot_repair_failed_onset_history():
    q={'states':[{'accepted':True,'requested_time':.012},{'accepted':False,'requested_time':.0121},{'accepted':True,'requested_time':.015}]}
    assert qualified_onset_prefix(q) is None


def test_historical_maximum_without_transition_proof_is_insufficient():
    assert qualified_onset_prefix({'states':[{'accepted':True,'requested_time':.012575}]}) is None


def test_provenance_or_output_failure_blocks_material_promotion():
    assert qualified_onset_prefix({'failures':['Changed RST'],'states':[{'accepted':True,'requested_time':.015}]}) is None
