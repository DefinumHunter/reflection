`timescale 1ns/1ps

module tb_sqrt_postprocess;
    logic        clk;
    logic        rst_n;
    logic signed [40:0] x_out_k;
    logic signed [5:0]  shift_n;
    logic  [3:0] local_id;
    logic        in_valid;
    logic signed [31:0] sqrt_result;
    logic  [3:0] local_id_out;
    logic        out_valid;

    sqrt_postprocess dut (.*);

    initial begin
        $dumpfile("waves.vcd");
        $dumpvars(0, tb_sqrt_postprocess);
    end
endmodule
