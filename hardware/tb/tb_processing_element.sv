`timescale 1ns / 1ps

// Reflection drives inputs and samples outputs of the full processing element.
module tb_processing_element;
    parameter int PIPELINE_STAGES = 4;
    parameter bit CHECK_NEIGHBOR = 1;

    logic               clk;
    logic               rst_n;

    logic signed [31:0] in_a;
    logic signed [31:0] in_b;
    logic signed [31:0] local_data;
    logic        [1:0]  sel;
    logic               sub_pre;
    logic               issue_vld;
    logic               ring_final;
    logic               sub_post;
    logic        [3:0]  in_id;

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

    processing_element #(
        .PIPELINE_STAGES (PIPELINE_STAGES),
        .CHECK_NEIGHBOR   (CHECK_NEIGHBOR)
    ) dut (.*);

    initial begin
        $dumpfile("waves.vcd");
        $dumpvars(0, tb_processing_element);
    end
endmodule
