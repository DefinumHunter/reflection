module w_normalize #(
    parameter int W_Q16  = 32,
    parameter int GUARD_HI = 4,
    parameter int GUARD_LO = 5,
    parameter int W_INT  = W_Q16 + GUARD_HI + GUARD_LO,
    parameter int NW     = 6
)(
    input  logic                    clk,
    input  logic                    rst_n,

    input  logic signed [W_Q16-1:0] w_in,
    input  logic         [3:0]      local_id,
    input  logic                    in_valid,

    output logic signed [W_INT-1:0] w_norm,
    output logic signed [NW-1:0]    shift_n,
    output logic         [3:0]      local_id_out,
    output logic                    out_valid
);

    logic signed [W_INT-1:0] w_ext;
    assign w_ext = { {GUARD_HI{w_in[W_Q16-1]}}, w_in, {GUARD_LO{1'b0}} };

    logic [$clog2(W_INT)-1:0] msb_pos;
    logic                     found;

    always_comb begin
        msb_pos = '0;
        found   = 1'b0;
        for (int i = W_INT-1; i >= 0; i--) begin
            if (!found && w_ext[i]) begin
                msb_pos = i[$clog2(W_INT)-1:0];
                found   = 1'b1;
            end
        end
    end

    localparam int POINT_BIT = 16 + GUARD_LO;
    logic signed [NW-1:0] e;
    assign e = NW'($signed({1'b0, msb_pos})) - NW'(POINT_BIT);

    logic signed [NW-1:0] n_comb;
    assign n_comb = e[0] ? (e >>> 1) + NW'(1) : (e >>> 1);

    logic signed [NW:0]        shift_amt;
    logic [$clog2(W_INT)-1:0]  shift_mag;
    logic signed [W_INT-1:0]   w_norm_comb;

    assign shift_amt = {n_comb, 1'b0};
    assign shift_mag = shift_amt[NW] ? (~shift_amt + 1'b1) : shift_amt;

    assign w_norm_comb = shift_amt[NW]
                        ? (w_ext <<< shift_mag)
                        : (w_ext >>> shift_mag);

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            w_norm       <= '0;
            shift_n      <= '0;
            local_id_out <= '0;
            out_valid    <= 1'b0;
        end else begin
            w_norm       <= found ? w_norm_comb : '0;
            shift_n      <= n_comb;
            local_id_out <= local_id;
            out_valid    <= in_valid;
        end
    end

endmodule
