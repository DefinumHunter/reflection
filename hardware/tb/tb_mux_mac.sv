module tb_mux_mac;
parameter int PIPELINE_STAGES=4;
logic clk,rst_n;
logic signed [31:0] in_a,in_b,local_data;
logic [1:0] sel;
logic sub_pre,issue_vld,ring_final,sub_post;
logic [3:0] in_id;
logic out_vld;
logic signed [31:0] out_res;
logic [3:0] out_id;
logic out_ring_final,out_sub_post,busy;
mux_mac #(.PIPELINE_STAGES(PIPELINE_STAGES)) dut (.*);
endmodule
