`timescale 1ns / 1ps

// Reflection TB, made by Engine/MakeTb.py from the ports of cmd_parser.
// No logic here: the bench drives and samples these signals.

module tb_cmd_parser;
    logic       clk;
    logic       rst_n;
    logic       frame_vld;
    logic [4:0] cmd;
    logic [1:0] sel;
    logic       sub_pre;
    logic       issue_vld;
    logic       ring_final;
    logic       sub_post;

    cmd_parser dut (.*);

    initial begin
        $dumpfile("waves.vcd");
        $dumpvars(0, tb_cmd_parser);
    end
endmodule
