`timescale 1ns / 1ps

// Reflection TB, made by Engine/MakeTb.py from the ports of div_postprocess.
// No logic here: the bench drives and samples these signals.
// Port widths depend on parameters: they are for the default values.

module tb_div_postprocess;
    parameter int W_INT = 41;
    parameter int W_Q16 = 32;
    parameter int GUARD_HI = 4;
    parameter int GUARD_LO = 5;
    parameter int NW = 6;

    logic               clk;
    logic               rst_n;
    logic signed [40:0] q_in;
    logic signed [5:0]  shift_r;
    logic               doubled;
    logic [3:0]         local_id;
    logic               in_valid;
    logic signed [31:0] inv_r_result;
    logic [3:0]         local_id_out;
    logic               out_valid;

    div_postprocess #(.W_INT(W_INT), .W_Q16(W_Q16), .GUARD_HI(GUARD_HI), .GUARD_LO(GUARD_LO), .NW(NW)) dut (.*);

    initial begin
        $dumpfile("waves.vcd");
        $dumpvars(0, tb_div_postprocess);
    end
endmodule
