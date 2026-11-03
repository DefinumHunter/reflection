`timescale 1ns / 1ps

module tb_pe_mac_wrapper;
    parameter int PIPELINE_STAGES = 4;

    logic               clk;
    logic               rst_n;

    // Входы для pe_input_mux
    logic signed [31:0] local_data;
    logic               sub;
    logic signed [31:0] in_a;
    logic signed [31:0] in_b;
    logic        [1:0]  sel;
    logic        [3:0]  in_id;
    logic               issue_vld;
    logic               mac_sel_in;

    // Выходы mac
    logic               out_vld;
    logic               out_sel;
    logic signed [31:0] out_res;
    logic        [3:0]  out_id;
    logic               busy;

    pe_mac_wrapper #(
        .PIPELINE_STAGES(PIPELINE_STAGES)
    ) dut (.*);

    initial begin
        $dumpfile("waves.vcd");
        $dumpvars(0, tb_pe_mac_wrapper);
    end

endmodule
