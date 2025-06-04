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

# h = pyrtl.Register(4, name='rob_h') #oldest val entry
# t = pyrtl.Register(4, name='rob_t') #next free
# count = pyrtl.Register(5, name='rob_count') #valid entries

# full = count == 16
# empty = count == 0

# head_is_being_filled = rob_fill_val_i & (h == rob_fill_slot_i)
# entry_ready = rob_valid[h] & ~rob_pending[h] & ~head_is_being_filled
# commit_fire = (~empty) & entry_ready       

# space_avail = count < 16
# rob_alloc_req_rdy_o <<= space_avail           
# alloc_fire = rob_alloc_req_val_i & space_avail  

# rob_alloc_resp_slot_o <<= t

# rob_commit_wen_o <<= commit_fire
# rob_commit_slot_o <<= h
# rob_commit_rf_waddr_o <<= rob_preg[h]

# with pyrtl.conditional_assignment:
#     with alloc_fire:
#         rob_valid[t]<<= 1
#         rob_pending[t] <<= 1
#         rob_preg[t] <<= rob_alloc_req_preg_i
#     with rob_fill_val_i:
#         rob_pending[rob_fill_slot_i] <<= 0

# t_next = pyrtl.select(t == 15, 0, t+1)
# h_next = pyrtl.select(h == 15, 0, h+1)

# t.next <<= pyrtl.select(alloc_fire, t_next, t)    
# h.next <<= pyrtl.select(commit_fire, h_next, h)

# count.next <<= count + alloc_fire - commit_fire



h = pyrtl.Register(bitwidth=4, name='h')
t = pyrtl.Register(bitwidth=4, name='t')

s_avail = pyrtl.WireVector(bitwidth=1, name='s_avail')
s_avail <<= ~rob_valid[t]


rob_alloc_req_rdy_o <<= s_avail
#t.next <<= t+1   
alloc_fire = pyrtl.WireVector(bitwidth=1, name='alloc_fire')
alloc_fire <<= s_avail & rob_alloc_req_val_i

with pyrtl.conditional_assignment:
    with alloc_fire:
        rob_pending[t] |= 1
        rob_valid[t] |= 1
        rob_preg[t] |= rob_alloc_req_preg_i
        rob_alloc_resp_slot_o |= t
        t.next |= t+1

with pyrtl.conditional_assignment:
    with rob_fill_val_i:
        rob_pending[rob_fill_slot_i] |= 0

commit_fire = pyrtl.WireVector(bitwidth=1, name='commit_fire')
commit_fire <<= rob_valid[h] & ~rob_pending[h]

with pyrtl.conditional_assignment:
    with commit_fire:
        h.next |= h+1  
        rob_commit_wen_o |= 1
        rob_valid[h] |= 0
        #h_is_last = h == 15
        # with h_is_last:
        #     h.next |= 0
        # with pyrtl.otherwise:
        #     h.next |= h + 1
    with ~commit_fire:
        rob_commit_wen_o |= 0
    
#t.next <<= t + alloc_fire 
#t.next <<= pyrtl.select(alloc_fire, t + 1, t) #fixes - only advance when fye=1, sike
rob_commit_slot_o <<= h
rob_commit_rf_waddr_o <<= rob_preg[h]




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





