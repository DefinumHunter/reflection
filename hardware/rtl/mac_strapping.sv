`timescale 1ns / 1ps

// Structural integration: Q16.16 MAC followed by output strapping.
// The neighbor stream is externally aligned to the MAC result.
module mac_strapping #(
    parameter int PIPELINE_STAGES = 4,
    parameter bit CHECK_NEIGHBOR = 1
) (
    input  logic               clk,
    input  logic               rst_n,

    input  logic               in_vld,
    input  logic signed [31:0] in_a,
    input  logic signed [31:0] in_b,
    input  logic        [3:0]  in_id,
    input  logic               in_ring_final,
    input  logic               in_sub_post,

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

    logic signed [31:0] mac_res;
    logic               mac_vld;
    logic        [3:0]  mac_id;
    logic               mac_ring_final;
    logic               mac_sub_post;

    mac_q16 #(
        .PIPELINE_STAGES (PIPELINE_STAGES)
    ) u_mac (
        .clk            (clk),
        .rst_n          (rst_n),
        .in_vld         (in_vld),
        .in_a           (in_a),
        .in_b           (in_b),
        .in_id          (in_id),
        .in_ring_final  (in_ring_final),
        .in_sub_post    (in_sub_post),
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
