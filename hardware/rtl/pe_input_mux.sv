`timescale 1ns / 1ps

// pe_input_mux: input stage of a processing element.
// Picks the two MAC operands (optionally a saturated pre-sum) and hands them
// to mac_q16 together with the transaction's valid, id and command flags.
// Full description: docs/pe_input_mux.md
//
// Protocol (one operation = 1 or 2 input clocks):
//   a*b       : clock 1: sel=00, in_a=a, in_b=b,         issue_vld=1
//   a*local   : clock 1: sel=11, in_a=a, local_data=l,   issue_vld=1
//   (a+-b)*c  : clock 1: sel=01, in_a=a, in_b=b, sub_pre=+-
//               clock 2: sel=10, in_a=c, sub_pre=+-,     issue_vld=1
// issue_vld comes in the clock of the LAST load of the operation.
// in_id, ring_final, sub_post are taken in that same clock.
// Outputs: 2 clocks after the issue clock, all together, with out_vld=1.

module pe_input_mux (
    input  logic               clk,
    input  logic               rst_n,

    // operands
    input  logic signed [31:0] in_a,
    input  logic signed [31:0] in_b,
    input  logic signed [31:0] local_data,

    // command (from cmd_parser)
    input  logic        [1:0]  sel,         // 00 a*b, 01 load sum, 10 sum*c, 11 a*local
    input  logic               sub_pre,     // pre-sum: 0 = a+b, 1 = a-b
    input  logic               issue_vld,   // operation complete, send it to the MAC
    input  logic               ring_final,  // passed through to pe_output_strapping
    input  logic               sub_post,    // passed through to pe_output_strapping
    input  logic        [3:0]  in_id,

    // to mac_q16
    output logic signed [31:0] a_out,
    output logic signed [31:0] b_out,
    output logic               out_vld,
    output logic               out_ring_final,
    output logic               out_sub_post,
    output logic        [3:0]  out_id
);

    localparam logic [1:0] SEL_AB    = 2'b00;
    localparam logic [1:0] SEL_SUM   = 2'b01;
    localparam logic [1:0] SEL_SUM_C = 2'b10;
    localparam logic [1:0] SEL_LOCAL = 2'b11;

    // ---------------- pre-sum: (sum1 +- sum2), saturated ----------------
    logic signed [31:0] sum1_reg, sum2_reg;
    logic signed [32:0] sum_ext;
    logic signed [31:0] sum_sat;

    assign sum_ext = sub_pre ? (33'(sum1_reg) - 33'(sum2_reg))
                             : (33'(sum1_reg) + 33'(sum2_reg));

    always_comb begin
        if (sum_ext[32] != sum_ext[31])
            sum_sat = sum_ext[32] ? 32'sh8000_0000 : 32'sh7FFF_FFFF;
        else
            sum_sat = sum_ext[31:0];
    end

    // ---------------- stage 1: operands and flags of the operation -----
    logic signed [31:0] op1_reg, op2_reg;
    logic        [3:0]  id_reg;
    logic               ring_reg, subpost_reg;
    logic               vld_reg;            // issue_vld, one clock later

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            sum1_reg <= '0;
            sum2_reg <= '0;
            op1_reg  <= '0;
            op2_reg  <= '0;
            vld_reg  <= 1'b0;
        end else begin
            vld_reg <= issue_vld;

            if (sel == SEL_SUM) begin
                sum1_reg <= in_a;
                sum2_reg <= in_b;
            end

            case (sel)
                SEL_AB:    begin op1_reg <= in_a; op2_reg <= in_b;       end
                SEL_SUM_C: begin op1_reg <= in_a; op2_reg <= sum_sat;    end
                SEL_LOCAL: begin op1_reg <= in_a; op2_reg <= local_data; end
                default: ;                                       // SEL_SUM: hold
            endcase
        end

        // flags have no reset: they are only used together with the valid
        if (issue_vld) begin
            id_reg      <= in_id;
            ring_reg    <= ring_final;
            subpost_reg <= sub_post;
        end
    end

    // ---------------- stage 2: output register to the MAC --------------
    always_ff @(posedge clk) begin
        if (!rst_n) begin
            out_vld <= 1'b0;
        end else begin
            out_vld <= vld_reg;
        end

        a_out <= op1_reg;
        b_out <= op2_reg;
        if (vld_reg) begin
            out_id         <= id_reg;
            out_ring_final <= ring_reg;
            out_sub_post   <= subpost_reg;
        end
    end

endmodule
