`timescale 1ns / 1ps

// Reflection TB, made by Engine/MakeTb.py from the ports of w_normalize.
// No logic here: the bench drives and samples these signals.
// Port widths depend on parameters: they are for the default values.

module tb_w_normalize;
    parameter int W_Q16 = 32;
    parameter int GUARD_HI = 4;
    parameter int GUARD_LO = 5;
    parameter int W_INT = 41;
    parameter int NW = 6;

    logic               clk;
    logic               rst_n;
    logic signed [31:0] w_in;
    logic [3:0]         local_id;
    logic               in_valid;
    logic signed [40:0] w_norm;
    logic signed [5:0]  shift_n;
    logic [3:0]         local_id_out;
    logic               out_valid;

    w_normalize #(.W_Q16(W_Q16), .GUARD_HI(GUARD_HI), .GUARD_LO(GUARD_LO), .W_INT(W_INT), .NW(NW)) dut (.*);

    initial begin
        $dumpfile("waves.vcd");
        $dumpvars(0, tb_w_normalize);
    end
endmodule
