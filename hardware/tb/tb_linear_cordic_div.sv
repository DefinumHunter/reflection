`timescale 1ns/1ps

module tb_linear_cordic_div;
    logic        clk;
    logic        rst_n;
    logic signed [40:0] r_norm;
    logic signed [5:0]  shift_r;
    logic  [3:0] local_id;
    logic        in_valid;
    logic signed [40:0] q_out;
    logic signed [5:0]  shift_r_out;
    logic  [3:0] local_id_out;
    logic        doubled_out;   // <-- добавлено
    logic        out_valid;

    linear_cordic_div dut (.*);

    initial begin
        $dumpfile("waves.vcd");
        $dumpvars(0, tb_linear_cordic_div);
    end
endmodule