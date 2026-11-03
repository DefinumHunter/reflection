module pe_output_strapping (
    input  logic               clk,
    input  logic               rst_n,

    input  logic signed [31:0] mac_res,
    input  logic signed [31:0] neighbor_res,
    input  logic               sel,
    input  logic               in_valid,

    input  logic        [3:0] in_id_self,
    input  logic        [3:0] in_id_neighbor,

    output logic signed [31:0] out,
    output logic        [3:0]  out_id,

    output logic               out_valid_ring,
    output logic               out_valid_final,

    output logic               idle,
    output logic               error
);

    logic signed [31:0] mac_res_reg;
    logic signed [31:0] neighbor_res_reg;
    logic               sel_reg;
    logic               valid_reg;
    logic        [3:0]  inner_id;

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            valid_reg <= 1'b0;
            error <= 1'b0;
        end else begin
            if(in_id_self == in_id_neighbor) begin
                valid_reg <= in_valid;
            end else begin
                valid_reg <= 1'b0;
                error <= 1'b1;
            end
        end

        mac_res_reg      <= mac_res;
        neighbor_res_reg <= neighbor_res;
        sel_reg          <= sel;
        inner_id         <= in_id_self;
    end

    logic signed [32:0] sum;
    logic signed [31:0] saturated;

    assign sum = 33'(mac_res_reg) + 33'(neighbor_res_reg);

    always_comb begin
        if (sum[32] != sum[31]) begin
            saturated = sum[32] ? 32'sh8000_0000 : 32'sh7FFF_FFFF;
        end else begin
            saturated = sum[31:0];
        end
    end

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            out_valid_ring  <= 1'b0;
            out_valid_final <= 1'b0;
        end else begin
            out_valid_ring  <= sel_reg  & valid_reg;
            out_valid_final <= ~sel_reg & valid_reg;
        end
        out_id <= inner_id;
        out <= saturated;
    end

    assign idle = !valid_reg && !out_valid_ring && !out_valid_final;

endmodule
