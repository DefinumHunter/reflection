`timescale 1ns / 1ps

module tb_vec_reg;
    logic       clk;
    logic       rst_n;
    logic [7:0] a [0:2];
    logic [7:0] k;
    wire  [7:0] y [0:2];      // output arrays are wires: Icarus does not pass them to a logic
    wire  [7:0] s;

    vec_reg dut (.*);
endmodule
