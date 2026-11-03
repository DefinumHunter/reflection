`timescale 1ns / 1ps

// Reflection TB, made by Engine/MakeTb.py from the ports of linear_cordic_div.
// No logic here: the bench drives and samples these signals.
// Port widths depend on parameters: they are for the default values.

module tb_linear_cordic_div;
    parameter int W_INT = 41;
    parameter int GUARD_LO = 5;
    parameter int AW = 41;
    parameter int NW = 6;
    parameter int N = 22;

    logic               clk;
    logic               rst_n;
    logic signed [40:0] r_norm;
    logic signed [5:0]  shift_r;
    logic [3:0]         local_id;
    logic               in_valid;
    logic signed [40:0] q_out;
    logic signed [5:0]  shift_r_out;
    logic [3:0]         local_id_out;
    logic               doubled_out;
    logic               out_valid;

    linear_cordic_div #(.W_INT(W_INT), .GUARD_LO(GUARD_LO), .AW(AW), .NW(NW), .N(N)) dut (.*);

    initial begin
        $dumpfile("waves.vcd");
        $dumpvars(0, tb_linear_cordic_div);
    end
endmodule
