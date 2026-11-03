`timescale 1ns/1ps

module tb_cmd_parser;
    logic       clk;
    logic       rst_n;
    logic       frame_vld;
    logic [4:0] cmd;
    logic [1:0] sel;
    logic       sub_pre;
    logic       issue_vld;
    logic       ring_final;
    logic       sub_post;

    cmd_parser dut (.*);

    // SVA/checker instantiation. Icarus doesn't support `bind`, so the
    // checker is instantiated directly here instead; waiting_c is an
    // internal (non-port) signal, connected via hierarchical reference
    // into the dut instance.
    cmd_parser_sva_icarus u_cmd_parser_sva_icarus (
        .clk(clk),
        .rst_n(rst_n),
        .frame_vld(frame_vld),
        .cmd(cmd),
        .sel(sel),
        .sub_pre(sub_pre),
        .issue_vld(issue_vld),
        .ring_final(ring_final),
        .sub_post(sub_post),
        .waiting_c(dut.waiting_c)
    );

    initial begin
        $dumpfile("waves.vcd");
        $dumpvars(0, tb_cmd_parser);
    end
endmodule
