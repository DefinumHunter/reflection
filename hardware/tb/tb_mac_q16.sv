`timescale 1ns / 1ps

// Reflection TB, made by Engine/MakeTb.py from the ports of mac_q16.
// No logic here: the bench drives and samples these signals.

module tb_mac_q16;
    parameter int PIPELINE_STAGES = 4;

    logic               clk;
    logic               rst_n;

    logic               in_vld;
    logic signed [31:0] in_a;
    logic signed [31:0] in_b;
    logic        [3:0]  in_id;
    logic               in_ring_final;
    logic               in_sub_post;

    logic               out_vld;
    logic signed [31:0] out_res;
    logic        [3:0]  out_id;
    logic               out_ring_final;
    logic               out_sub_post;
    logic               busy;

    mac_q16 #(.PIPELINE_STAGES(PIPELINE_STAGES)) dut (.*);

    initial begin
        $dumpfile("waves.vcd");
        $dumpvars(0, tb_mac_q16);
    end
endmodule