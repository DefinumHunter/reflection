`timescale 1ns / 1ps

// Reflection TB, made by Engine/MakeTb.py from the ports of winnower.
// No logic here: the bench drives and samples these signals.
// Port widths depend on parameters: they are for the default values.

module tb_winnower;
    parameter int NUM_SLOTS = 9;
    parameter int GROUPS = 3;

    logic               clk;
    logic               rst_n;
    logic signed [31:0] win_data [0:8];
    logic [3:0]         win_id [0:8];
    logic               win_valid [0:8];
    logic signed [31:0] cordic_data [0:2];
    logic [3:0]         cordic_id [0:2];
    logic               cordic_valid [0:2];
    wire  signed [31:0] out_data [0:8];
    wire  [3:0]         out_id [0:8];
    logic [31:0]        crc32;
    logic               out_valid;

    winnower #(.NUM_SLOTS(NUM_SLOTS), .GROUPS(GROUPS)) dut (.*);

    initial begin
        $dumpfile("waves.vcd");
        $dumpvars(0, tb_winnower);
    end
endmodule
