module mux_mac #(parameter int PIPELINE_STAGES=4)(
input logic clk,rst_n,
input logic signed [31:0] in_a,in_b,local_data,
input logic [1:0] sel,
input logic sub_pre,issue_vld,ring_final,sub_post,
input logic [3:0] in_id,
output logic out_vld,
output logic signed [31:0] out_res,
output logic [3:0] out_id,
output logic out_ring_final,out_sub_post,busy
);
logic signed [31:0] mux_a,mux_b;
logic mux_vld,mux_ring_final,mux_sub_post;
logic [3:0] mux_id;
pe_input_mux u_mux(
.clk(clk),.rst_n(rst_n),.in_a(in_a),.in_b(in_b),.local_data(local_data),
.sel(sel),.sub_pre(sub_pre),.issue_vld(issue_vld),
.ring_final(ring_final),.sub_post(sub_post),.in_id(in_id),
.a_out(mux_a),.b_out(mux_b),.out_vld(mux_vld),
.out_ring_final(mux_ring_final),.out_sub_post(mux_sub_post),.out_id(mux_id));
mac_q16 #(.PIPELINE_STAGES(PIPELINE_STAGES)) u_mac(
.clk(clk),.rst_n(rst_n),.in_vld(mux_vld),.in_a(mux_a),.in_b(mux_b),
.in_id(mux_id),.in_ring_final(mux_ring_final),.in_sub_post(mux_sub_post),
.out_vld(out_vld),.out_res(out_res),.out_id(out_id),
.out_ring_final(out_ring_final),.out_sub_post(out_sub_post),.busy(busy));
endmodule
