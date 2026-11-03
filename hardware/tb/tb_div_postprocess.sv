`timescale 1ns/1ps

module tb_div_postprocess;
    logic        clk;
    logic        rst_n;
    logic signed [40:0] q_in;
    logic signed [5:0]  shift_r;
    logic        doubled;
    logic  [3:0] local_id;
    logic        in_valid;
    logic signed [31:0] inv_r_result;
    logic  [3:0] local_id_out;
    logic        out_valid;

    div_postprocess dut (.*);

    initial begin
        $dumpfile("waves.vcd");
        $dumpvars(0, tb_div_postprocess);
    end
endmodule
