# ucsbcs154lab9
# All Rights Reserved
# Copyright (c) 2023 Jonathan Balkind
# Distribution Prohibited
import pyrtl
### Alloc Interface ###
# Is the alloc req valid?
rob_alloc_req_val_i = pyrtl.Input(bitwidth=1, name="rob_alloc_req_val_i")
# Incoming Instruction's Physical dest reg
rob_alloc_req_preg_i = pyrtl.Input(bitwidth=5, name="rob_alloc_req_preg_i")
# Is the ROB ready to accept an incoming request?
rob_alloc_req_rdy_o = pyrtl.Output(bitwidth=1, name="rob_alloc_req_rdy_o")
# The assigned ROB slot
rob_alloc_resp_slot_o = pyrtl.Output(bitwidth=4, name="rob_alloc_resp_slot_o")
### Writeback Interface ###
# Is writeback occuring?
rob_fill_val_i = pyrtl.Input(bitwidth=1, name="rob_fill_val_i")
# In which slot is writeback occurring?
rob_fill_slot_i = pyrtl.Input(bitwidth=4, name="rob_fill_slot_i")
### Commit Interface ###
# Is an entry being committed this cycle?
rob_commit_wen_o = pyrtl.Output(bitwidth=1, name="rob_commit_wen_o")
# ROB slot that's committed
rob_commit_slot_o = pyrtl.Output(bitwidth=4, name="rob_commit_slot_o")
# Physical register that's committed
rob_commit_rf_waddr_o = pyrtl.Output(bitwidth=5, name="rob_commit_rf_waddr_o")
# metadata managed by this module, don't modify names/ports or make async!
rob_valid = pyrtl.MemBlock(bitwidth=1, addrwidth=4, name="rob_valid",
max_write_ports=2)
rob_pending = pyrtl.MemBlock(bitwidth=1, addrwidth=4, name="rob_pending",
max_write_ports=2)
rob_preg = pyrtl.MemBlock(bitwidth=5, addrwidth=4, name="rob_preg")

#---------------------------------------------------------------------------------------

h = pyrtl.Register(4, name='rob_h') #oldest val entry
t = pyrtl.Register(4, name='rob_t') #next freee
count = pyrtl.Register(5, name='rob_count') #valid entries

full = count == 16 
empty = count == 0

not_full  = rob_alloc_req_val_i & ~full #rob aint full
entry_ready = rob_valid[h] & ~rob_pending[h]
commit = (~empty) & entry_ready      

rob_alloc_req_rdy_o <<= ~full #atleast one free spot
rob_alloc_resp_slot_o <<= t

rob_commit_wen_o <<= commit
rob_commit_slot_o <<= h
rob_commit_rf_waddr_o <<= rob_preg[h]

with pyrtl.conditional_assignment:
    with not_full:                           
        rob_valid[t] <<= 1
        rob_pending[t] <<= 1
        rob_preg[t] <<= rob_alloc_req_preg_i
    with rob_fill_val_i:                     
        rob_pending[rob_fill_slot_i] <<= 0

t.next <<= pyrtl.select(not_full,  t+1,  t)
h.next <<= pyrtl.select(commit, h+1, h)

increase = not_full & ~commit             
decrease = commit & ~not_full   
#if both fire the +1 -1 cancel out           
count.next <<= count + increase - decrease


#---------------------------------------------------------------------------------------
### Testing and Simulation ###
def TestOneInstructionFullFlow():
    sim_trace = pyrtl.SimulationTrace()
    sim = pyrtl.Simulation(tracer=sim_trace)
    preg = 10
    # First allocate a slot in the ROB
    sim.step({
            rob_alloc_req_val_i: 1,
            rob_alloc_req_preg_i: preg,
            rob_fill_val_i: 0,
            rob_fill_slot_i: 0,
        })
    assert(sim.inspect("rob_alloc_req_rdy_o") == 1)
    assignedSlot = sim.inspect("rob_alloc_resp_slot_o")
    # Then, writeback that slot (could be many cycles later but in this example just one)
    sim.step({
            rob_alloc_req_val_i: 0,
            rob_alloc_req_preg_i: 0,
            rob_fill_val_i: 1,
            rob_fill_slot_i: assignedSlot,
        })
    # We don't commit in the same cycle as writeback happens
    assert(sim.inspect("rob_commit_wen_o") == 0)
    sim.step({
            rob_alloc_req_val_i: 0,
            rob_alloc_req_preg_i: 0,
            rob_fill_val_i: 0,
            rob_fill_slot_i: 0,
        })
    # ...commit in the next cycle
    assert(sim.inspect("rob_commit_wen_o") == 1)
    assert(sim.inspect("rob_commit_slot_o") == assignedSlot)
    assert(sim.inspect("rob_commit_rf_waddr_o") == preg)
    # ROB stays ready
    assert(sim.inspect("rob_alloc_req_rdy_o") == 1)
    sim.step({
            rob_alloc_req_val_i: 0,
            rob_alloc_req_preg_i: 0,
            rob_fill_val_i: 0,
            rob_fill_slot_i: 0,
        })
    # but shouldn't commit anything in the following cycle!
    assert(sim.inspect("rob_commit_wen_o") == 0)
    # ...and ROB stays ready
    assert(sim.inspect("rob_alloc_req_rdy_o") == 1)
# Uncomment to run the Sample Test
# You may want to recomment before submitting as it could interfere with the autograder
if __name__ == "__main__":
    TestOneInstructionFullFlow()
    print("Pass TestOneInstructionFullFlow")