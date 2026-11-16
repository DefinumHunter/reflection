`timescale 1ns / 1ps

// Reflection testbench: input driving and output sampling are handled by Engine.
module tb_mux_mac;
    parameter int PIPELINE_STAGES = 4;

    logic               clk;
    logic               rst_n;

    logic signed [31:0] in_a;
    logic signed [31:0] in_b;
    logic signed [31:0] local_data;
    logic        [1:0]  sel;
    logic               sub_pre;
    logic               issue_vld;
    logic               ring_final;
    logic               sub_post;
    logic        [3:0]  in_id;

    logic               out_vld;
    logic signed [31:0] out_res;
    logic        [3:0]  out_id;
    logic               out_ring_final;
    logic               out_sub_post;
    logic               busy;

    mux_mac #(
        .PIPELINE_STAGES (PIPELINE_STAGES)
    ) dut (.*);

    initial begin
        $dumpfile("waves.vcd");
        $dumpvars(0, tb_mux_mac);
    end
endmodule
