`timescale 1ns / 1ps

// Reflection TB, made by Engine/MakeTb.py from the ports of hyperbolic_cordic_sqrt.
// No logic here: the bench drives and samples these signals.
// Port widths depend on parameters: they are for the default values.

module tb_hyperbolic_cordic_sqrt;
    parameter int W_INT = 41;
    parameter int AW = 41;
    parameter int NW = 6;
    parameter int N = 22;

    logic               clk;
    logic               rst_n;
    logic signed [40:0] w_norm;
    logic signed [5:0]  shift_n;
    logic [3:0]         local_id;
    logic               in_valid;
    logic signed [40:0] x_out_k;
    logic signed [40:0] y_out_k;
    logic signed [40:0] angle_out;
    logic signed [5:0]  shift_n_out;
    logic [3:0]         local_id_out;
    logic               out_valid;

    hyperbolic_cordic_sqrt #(.W_INT(W_INT), .AW(AW), .NW(NW), .N(N)) dut (.*);

    initial begin
        $dumpfile("waves.vcd");
        $dumpvars(0, tb_hyperbolic_cordic_sqrt);
    end
endmodule
