"""Coverage for both leaf models in the structural composition."""
from Engine.Coverage import Tag, Cross
from Modules.pe_input_mux.Coverage import selection,valid,preop,side,id_point,gaps,resets

mux_arithmetic=Tag("mux pre-sum operation",["sum_add","sum_sub"],at_least=5)
mux_saturation=Tag("mux pre-sum saturation",["sum_sat_none","sum_sat_pos","sum_sat_neg"],at_least=5)
mac_rounding=Tag("mac rounding",["round_down","round_up","round_tie_stay","round_tie_up"],at_least=3)
mac_saturation=Tag("mac saturation",["sat_none","sat_pos","sat_neg"],at_least=3)
POINTS=[selection,valid,preop,side,id_point,gaps,resets,
        Cross(selection,valid),mux_arithmetic,mux_saturation,mac_rounding,mac_saturation]
