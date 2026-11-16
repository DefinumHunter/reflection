`timescale 1ns / 1ps

// Reflection drives and samples the DUT ports.
module tb_mac_strapping;
    parameter int PIPELINE_STAGES = 4;
    parameter bit CHECK_NEIGHBOR = 1;

    logic               clk;
    logic               rst_n;

    logic               in_vld;
    logic signed [31:0] in_a;
    logic signed [31:0] in_b;
    logic        [3:0]  in_id;
    logic               in_ring_final;
    logic               in_sub_post;

    logic signed [31:0] neighbor_res;
    logic               neighbor_vld;
    logic        [3:0]  neighbor_id;

    logic signed [31:0] out;
    logic        [3:0]  out_id;
    logic               out_valid_ring;
    logic               out_valid_final;
    logic               idle;
    logic               error;
    logic               busy;

    mac_strapping #(
        .PIPELINE_STAGES (PIPELINE_STAGES),
        .CHECK_NEIGHBOR   (CHECK_NEIGHBOR)
    ) dut (.*);

    initial begin
        $dumpfile("waves.vcd");
        $dumpvars(0, tb_mac_strapping);
    end
endmodule
