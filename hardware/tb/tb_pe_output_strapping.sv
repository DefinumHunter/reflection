`timescale 1ns / 1ps

// Reflection TB, made by Engine/MakeTb.py from the ports of pe_output_strapping.
// No logic here: the bench drives and samples these signals.

module tb_pe_output_strapping;
    logic               clk;
    logic               rst_n;
    logic signed [31:0] mac_res;
    logic signed [31:0] neighbor_res;
    logic               sel;
    logic               in_valid;
    logic [3:0]         in_id_self;
    logic [3:0]         in_id_neighbor;
    logic signed [31:0] out;
    logic [3:0]         out_id;
    logic               out_valid_ring;
    logic               out_valid_final;
    logic               idle;
    logic               error;

    pe_output_strapping dut (.*);

    initial begin
        $dumpfile("waves.vcd");
        $dumpvars(0, tb_pe_output_strapping);
    end
endmodule
