`timescale 1ns / 1ps

// mac_q16: Q16.16 multiplier of a processing element.
// out_res = round_half_even(in_a * in_b / 2^16), saturated to signed 32 bit.
// The transaction's id and command flags travel through the pipeline with
// the valid, so they come out in the same clock as the product.
// Full description: docs/mac_q16.md
//
// Latency: PIPELINE_STAGES clocks from in_vld to out_vld, one product per clock.

module mac_q16 #(
    parameter int PIPELINE_STAGES = 4
) (
    input  logic               clk,
    input  logic               rst_n,

    input  logic               in_vld,
    input  logic signed [31:0] in_a,
    input  logic signed [31:0] in_b,
    input  logic        [3:0]  in_id,
    input  logic               in_ring_final,   // passed through to pe_output_strapping
    input  logic               in_sub_post,     // passed through to pe_output_strapping

    output logic               out_vld,
    output logic signed [31:0] out_res,
    output logic        [3:0]  out_id,
    output logic               out_ring_final,
    output logic               out_sub_post,
    output logic               busy             // a product is being computed (comb)
);

    // id and flags as one side word: {id, ring_final, sub_post}
    localparam int SIDE_W = 6;

    // ---------------- pipeline ----------------
    logic signed [63:0]       mult_comb;
    logic signed [63:0]       pipe      [0:PIPELINE_STAGES-1];
    logic                     vld_pipe  [0:PIPELINE_STAGES-1];
    logic        [SIDE_W-1:0] side_pipe [0:PIPELINE_STAGES-1];

    assign mult_comb = in_a * in_b;

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            for (int i = 0; i < PIPELINE_STAGES; i++)
                vld_pipe[i] <= 1'b0;
        end else begin
            vld_pipe[0] <= in_vld;
            for (int i = 1; i < PIPELINE_STAGES; i++)
                vld_pipe[i] <= vld_pipe[i-1];
        end

        // product and side word have no reset: only read together with the valid
        pipe[0]      <= mult_comb;
        side_pipe[0] <= {in_id, in_ring_final, in_sub_post};
        for (int i = 1; i < PIPELINE_STAGES; i++) begin
            pipe[i]      <= pipe[i-1];
            side_pipe[i] <= side_pipe[i-1];
        end
    end

    // ---------------- rounding: half to even, at bit 16 ----------------
    logic signed [63:0] last_pipe;
    logic               guard, lsb, sticky, round;
    logic signed [48:0] ext_result;
    logic               overflow;

    assign last_pipe = pipe[PIPELINE_STAGES-1];
    assign guard     = last_pipe[15];
    assign lsb       = last_pipe[16];
    assign sticky    = |last_pipe[14:0];
    assign round     = guard & (sticky | lsb);

    assign ext_result = $signed(last_pipe[63:16]) + $signed({48'b0, round});

    // ---------------- saturation to signed 32 bit ----------------
    assign overflow = (ext_result[48:31] != {18{ext_result[31]}});

    always_comb begin
        if (overflow)
            out_res = last_pipe[63] ? 32'sh8000_0000 : 32'sh7FFF_FFFF;
        else
            out_res = ext_result[31:0];
    end

    // ---------------- outputs ----------------
    assign out_vld = vld_pipe[PIPELINE_STAGES-1];
    assign {out_id, out_ring_final, out_sub_post} = side_pipe[PIPELINE_STAGES-1];

    always_comb begin
        busy = in_vld;
        for (int i = 0; i < PIPELINE_STAGES; i++)
            busy = busy || vld_pipe[i];
    end

endmodule
