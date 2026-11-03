module pe_input_mux (
    input  logic               clk,
    input  logic               rst_n,

    input  logic signed [31:0] local_data,
    input  logic               sub,

    input  logic signed [31:0] in_a,
    input  logic signed [31:0] in_b,
    input  logic         [1:0] sel,

    input  logic         [4:0] in_id,
    input  logic               compare_id,

    input  logic               issue_vld,

    output logic signed [31:0] a_out,
    output logic signed [31:0] b_out,
    output logic         [4:0] out_id,
    output logic               out_vld
);

    logic signed [31:0] sum1_reg, sum2_reg;
    logic signed [31:0] mux1_reg, mux2_reg;

    logic [4:0] local_id_sum;
    logic [4:0] local_id_mux;

    logic signed [32:0] sum_ext;
    logic signed [31:0] sum_saturated;

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            sum1_reg <= '0;
            sum2_reg <= '0;
            mux1_reg <= '0;
            mux2_reg <= '0;
        end else begin
            if (sel == 2'b01) begin
                sum1_reg <= in_a;
                sum2_reg <= in_b;
            end

            case (sel)
                2'b00, 2'b10, 2'b11: begin
                    mux1_reg     <= in_a;
                    local_id_mux <= in_id;
                end
                default: ;
            endcase

            case (sel)
                2'b00:   mux2_reg <= in_b;
                2'b10:   mux2_reg <= sum_saturated;
                2'b11:   mux2_reg <= local_data;
                default: ;
            endcase
        end
    end

    assign sum_ext = sub ? (33'(sum1_reg) - 33'(sum2_reg))
                          : (33'(sum1_reg) + 33'(sum2_reg));

    always_comb begin
        if (sum_ext[32] != sum_ext[31])
            sum_saturated = sum_ext[32] ? 32'sh8000_0000 : 32'sh7FFF_FFFF;
        else
            sum_saturated = sum_ext[31:0];
    end

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            out_vld <= 1'b0;
        end else begin
            out_vld <= issue_vld;
            a_out   <= mux1_reg;
            b_out   <= mux2_reg;
            if (issue_vld) out_id <= local_id_mux;
        end
    end

endmodule
