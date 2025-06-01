"""
test_cases.py  –  Local functional tests for CS154 Lab‑9 ROB
------------------------------------------------------------
Run:  python3 test_cases.py
"""

import importlib
import pyrtl

# ────────────────────────────────────────────────────────────────────
# 1.  Load the student's design into a *fresh* working block
# ────────────────────────────────────────────────────────────────────
pyrtl.reset_working_block()                         # clear any previous wires
rob = importlib.import_module("ucsbcs154lab9_reorderbuffer")

# Friendly aliases for the four input wires
alloc_val  = rob.rob_alloc_req_val_i
alloc_preg = rob.rob_alloc_req_preg_i
fill_val   = rob.rob_fill_val_i
fill_slot  = rob.rob_fill_slot_i

# Mapping so we can use readable keywords
name2wire = {
    "alloc_val":  alloc_val,
    "alloc_preg": alloc_preg,
    "fill_val":   fill_val,
    "fill_slot":  fill_slot,
}

# ────────────────────────────────────────────────────────────────────
# 2. Helper: advance one cycle, defaulting every Input to 0
# ────────────────────────────────────────────────────────────────────
def _step(sim, **named):
    """Step simulation one clock; unspecified inputs default to 0.

    Usage:
        _step(sim, alloc_val=1, alloc_preg=5)
        _step(sim, fill_val=1, fill_slot=3)
    """
    defaults = {w: 0 for w in name2wire.values()}
    for k, v in named.items():
        defaults[name2wire[k]] = v
    sim.step(defaults)

# ────────────────────────────────────────────────────────────────────
# 3.  Unit‑tests covering the tricky cases
# ────────────────────────────────────────────────────────────────────
def TestOneInstructionFullFlow():
    sim = pyrtl.Simulation()
    preg = 10

    _step(sim, alloc_val=1, alloc_preg=preg)
    slot = sim.inspect("rob_alloc_resp_slot_o")

    _step(sim, fill_val=1, fill_slot=slot)
    assert sim.inspect("rob_commit_wen_o") == 0, "Committed too early"

    _step(sim)
    assert sim.inspect("rob_commit_wen_o")      == 1
    assert sim.inspect("rob_commit_slot_o")     == slot
    assert sim.inspect("rob_commit_rf_waddr_o") == preg

def TestReadySignalAfterFill():
    sim = pyrtl.Simulation()

    _step(sim, alloc_val=1, alloc_preg=1)
    slot = sim.inspect("rob_alloc_resp_slot_o")

    _step(sim, fill_val=1, fill_slot=slot)
    assert sim.inspect("rob_alloc_req_rdy_o") == 0, "ROB signalled ready in fill cycle"

    _step(sim)
    assert sim.inspect("rob_commit_wen_o") == 1
    assert sim.inspect("rob_alloc_req_rdy_o") == 1

def TestFullROBCommitFreesEntry():
    sim = pyrtl.Simulation()

    for p in range(16):
        _step(sim, alloc_val=1, alloc_preg=p)
    assert sim.inspect("rob_alloc_req_rdy_o") == 0, "ROB not full!"

    for i in range(16):
        head = sim.inspect("rob_commit_slot_o")
        _step(sim, fill_val=1, fill_slot=head)
        _step(sim)
        assert sim.inspect("rob_commit_wen_o") == 1, f"Commit {i} missing"

    assert sim.inspect("rob_alloc_req_rdy_o") == 1, "ROB not freed after commits"

def TestCommitSweep():
    sim = pyrtl.Simulation()
    n = 8

    for p in range(n):
        _step(sim, alloc_val=1, alloc_preg=p)
    for s in range(n):
        _step(sim, fill_val=1, fill_slot=s)

    commits = 0
    for _ in range(n + 2):
        _step(sim)
        commits += sim.inspect("rob_commit_wen_o")
    assert commits == n, f"Expected {n} commits, saw {commits}"

def TestIgnoreInvalidFill():
    sim = pyrtl.Simulation()

    _step(sim, alloc_val=1, alloc_preg=1)
    _step(sim, fill_val=1, fill_slot=7)          # bogus slot
    _step(sim)
    assert sim.inspect("rob_commit_wen_o") == 0, "Commit after invalid fill"

# ────────────────────────────────────────────────────────────────────
# 4.  Run all tests
# ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    TestOneInstructionFullFlow()
    TestReadySignalAfterFill()
    TestFullROBCommitFreesEntry()
    TestCommitSweep()
    TestIgnoreInvalidFill()
    print("\033[92mAll local ROB tests passed!\033[0m")
