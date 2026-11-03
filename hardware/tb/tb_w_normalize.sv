`timescale 1ns/1ps

module tb_w_normalize;
    logic        clk;
    logic        rst_n;
    logic signed [31:0] w_in;
    logic  [3:0] local_id;
    logic        in_valid;
    logic signed [40:0] w_norm;
    logic signed [5:0]  shift_n;
    logic  [3:0] local_id_out;
    logic        out_valid;

    w_normalize dut (.*);

    initial begin
        $dumpfile("waves.vcd");
        $dumpvars(0, tb_w_normalize);
    end
endmodule
