`timescale 1ns / 1ps

// Linear processing element: input mux -> Q16.16 MAC -> output strapping.
// The composite golden model is assembled automatically by Reflection.
module processing_element #(
    parameter int PIPELINE_STAGES = 4,
    parameter bit CHECK_NEIGHBOR = 1
) (
    input  logic               clk,
    input  logic               rst_n,

    input  logic signed [31:0] in_a,
    input  logic signed [31:0] in_b,
    input  logic signed [31:0] local_data,
    input  logic        [1:0]  sel,
    input  logic               sub_pre,
    input  logic               issue_vld,
    input  logic               ring_final,
    input  logic               sub_post,
    input  logic        [3:0]  in_id,

    input  logic signed [31:0] neighbor_res,
    input  logic               neighbor_vld,
    input  logic        [3:0]  neighbor_id,

    output logic signed [31:0] out,
    output logic        [3:0]  out_id,
    output logic               out_valid_ring,
    output logic               out_valid_final,
    output logic               idle,
    output logic               error,
    output logic               busy
);

    logic signed [31:0] mux_a;
    logic signed [31:0] mux_b;
    logic               mux_vld;
    logic        [3:0]  mux_id;
    logic               mux_ring_final;
    logic               mux_sub_post;

    logic signed [31:0] mac_res;
    logic               mac_vld;
    logic        [3:0]  mac_id;
    logic               mac_ring_final;
    logic               mac_sub_post;

    pe_input_mux u_mux (
        .clk            (clk),
        .rst_n          (rst_n),
        .in_a           (in_a),
        .in_b           (in_b),
        .local_data     (local_data),
        .sel            (sel),
        .sub_pre        (sub_pre),
        .issue_vld      (issue_vld),
        .ring_final     (ring_final),
        .sub_post       (sub_post),
        .in_id          (in_id),
        .a_out          (mux_a),
        .b_out          (mux_b),
        .out_vld        (mux_vld),
        .out_ring_final (mux_ring_final),
        .out_sub_post   (mux_sub_post),
        .out_id         (mux_id)
    );

    mac_q16 #(
        .PIPELINE_STAGES (PIPELINE_STAGES)
    ) u_mac (
        .clk            (clk),
        .rst_n          (rst_n),
        .in_vld         (mux_vld),
        .in_a           (mux_a),
        .in_b           (mux_b),
        .in_id          (mux_id),
        .in_ring_final  (mux_ring_final),
        .in_sub_post    (mux_sub_post),
        .out_vld        (mac_vld),
        .out_res        (mac_res),
        .out_id         (mac_id),
        .out_ring_final (mac_ring_final),
        .out_sub_post   (mac_sub_post),
        .busy           (busy)
    );

    pe_output_strapping #(
        .CHECK_NEIGHBOR (CHECK_NEIGHBOR)
    ) u_strapping (
        .clk             (clk),
        .rst_n           (rst_n),
        .mac_res         (mac_res),
        .mac_vld         (mac_vld),
        .mac_id          (mac_id),
        .mac_ring_final  (mac_ring_final),
        .mac_sub_post    (mac_sub_post),
        .neighbor_res    (neighbor_res),
        .neighbor_vld    (neighbor_vld),
        .neighbor_id     (neighbor_id),
        .out             (out),
        .out_id          (out_id),
        .out_valid_ring  (out_valid_ring),
        .out_valid_final (out_valid_final),
        .idle            (idle),
        .error           (error)
    );

endmodule
