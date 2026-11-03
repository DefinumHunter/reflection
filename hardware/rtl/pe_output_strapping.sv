`timescale 1ns / 1ps

// pe_output_strapping: output stage of a processing element.
// Adds the MAC product to the running sum that comes from the left neighbor
// (or subtracts it), saturates, and sends the result either on along the
// ring to the next PE or out of the array as final.
//
//   sub_post = 0: out = sat(neighbor + mac)
//   sub_post = 1: out = sat(neighbor - mac)
//   ring_final = 1: result goes to the next PE   (out_valid_ring)
//   ring_final = 0: result leaves the array      (out_valid_final)
//
// With CHECK_NEIGHBOR = 1 every valid product must meet a valid neighbor
// result with the same id; otherwise the product is dropped and error is set
// (sticky until reset). The first PE of a chain has no neighbor: use
// CHECK_NEIGHBOR = 0 and tie neighbor_res to 0.
// Full description: docs/pe_output_strapping.md
//
// Latency: 2 clocks from mac_vld to out_valid_ring / out_valid_final.

module pe_output_strapping #(
    parameter bit CHECK_NEIGHBOR = 1
) (
    input  logic               clk,
    input  logic               rst_n,

    // from mac_q16 of this PE
    input  logic signed [31:0] mac_res,
    input  logic               mac_vld,
    input  logic        [3:0]  mac_id,
    input  logic               mac_ring_final,
    input  logic               mac_sub_post,

    // from pe_output_strapping of the left neighbor (its out, out_valid_ring, out_id)
    input  logic signed [31:0] neighbor_res,
    input  logic               neighbor_vld,
    input  logic        [3:0]  neighbor_id,

    output logic signed [31:0] out,
    output logic        [3:0]  out_id,
    output logic               out_valid_ring,
    output logic               out_valid_final,
    output logic               idle,
    output logic               error
);

    // ---------------- stage 1: take both operands and the flags --------
    logic signed [31:0] mac_reg, neighbor_reg;
    logic        [3:0]  id_reg;
    logic               ring_reg, sub_reg;
    logic               valid_reg;
    logic               match;

    assign match = !CHECK_NEIGHBOR || (neighbor_vld && neighbor_id == mac_id);

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            valid_reg <= 1'b0;
            error     <= 1'b0;
        end else begin
            valid_reg <= mac_vld && match;
            if (mac_vld && !match)
                error <= 1'b1;
        end

        mac_reg      <= mac_res;
        neighbor_reg <= neighbor_res;
        id_reg       <= mac_id;
        ring_reg     <= mac_ring_final;
        sub_reg      <= mac_sub_post;
    end

    // ---------------- neighbor +- mac, saturated to signed 32 bit ------
    logic signed [32:0] sum;
    logic signed [31:0] saturated;

    assign sum = sub_reg ? (33'(neighbor_reg) - 33'(mac_reg))
                         : (33'(neighbor_reg) + 33'(mac_reg));

    always_comb begin
        if (sum[32] != sum[31])
            saturated = sum[32] ? 32'sh8000_0000 : 32'sh7FFF_FFFF;
        else
            saturated = sum[31:0];
    end

    // ---------------- stage 2: output register ----------------
    always_ff @(posedge clk) begin
        if (!rst_n) begin
            out_valid_ring  <= 1'b0;
            out_valid_final <= 1'b0;
        end else begin
            out_valid_ring  <=  ring_reg & valid_reg;
            out_valid_final <= !ring_reg & valid_reg;
        end
        out    <= saturated;
        out_id <= id_reg;
    end

    assign idle = !valid_reg && !out_valid_ring && !out_valid_final;

endmodule
