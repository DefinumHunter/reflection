`timescale 1ns/1ps

module tb_pe_input_mux;
    logic               clk;
    logic               rst_n;
    logic signed [31:0] local_data;
    logic               sub;
    logic signed [31:0] in_a;
    logic signed [31:0] in_b;
    logic         [1:0] sel;
    logic         [4:0] in_id;
    logic               compare_id;
    logic               issue_vld;
    logic signed [31:0] a_out;
    logic signed [31:0] b_out;
    logic         [4:0] out_id;
    logic               out_vld;

    pe_input_mux dut (.*);

    pe_input_mux_sva_icarus u_sva (.clk(clk), .rst_n(rst_n));

    initial begin
        $dumpfile("waves.vcd");
        $dumpvars(0, tb_pe_input_mux);
    end
endmodule
