module div_postprocess #(
    parameter int W_INT    = 41,
    parameter int W_Q16    = 32,
    parameter int GUARD_HI = 4,
    parameter int GUARD_LO = 5,
    parameter int NW       = 6
)(
    input  logic                    clk,
    input  logic                    rst_n,

    input  logic signed [W_INT-1:0] q_in,       // 1/r_norm (или 1/(2*r_norm), см. doubled), из linear_cordic_div
    input  logic signed [NW-1:0]    shift_r,    // тот же N, что применялся к R в w_normalize
    input  logic                    doubled,    // если 1 — linear_cordic_div считал 1/(2*r_norm), нужно удвоить
    input  logic         [3:0]      local_id,
    input  logic                    in_valid,

    output logic signed [W_Q16-1:0] inv_r_result, // 1/R, готовый Q16.16
    output logic         [3:0]      local_id_out,
    output logic                    out_valid
);

    // ---- Коррекция удвоения (см. linear_cordic_div): если алгоритм считал
    //      1/(2*r_norm) вместо 1/r_norm (случай r_norm<1.0, вне диапазона
    //      сходимости linear-mode при фиксированном y0=1.0) — компенсируем
    //      здесь, ДО применения сдвига по shift_r. ----
    logic signed [W_INT-1:0] q_corrected;
    assign q_corrected = doubled ? (q_in <<< 1) : q_in;

    // ---- Направление сдвига: 1/R = (1/R_norm) * 2^(-2N) ----
    // Это ТА ЖЕ сторона, что и у самого R->R_norm (не противоположная, как было для sqrt!):
    //   R = R_norm * 2^(2N)  =>  1/R = (1/R_norm) * 2^(-2N)
    // При N>=0 (R был большим, R_norm получен сдвигом ВПРАВО) — 1/R тоже сдвигаем ВПРАВО
    // на ПОЛНЫЕ 2N (не N, как у sqrt — там была связь через степень 1/2, здесь её нет).
    logic signed [NW:0]       shift2n;      // 2*shift_r, на бит шире под знак
    logic [$clog2(W_INT)-1:0] shift_mag;
    logic signed [W_INT-1:0]  shifted;

    assign shift2n   = {shift_r, 1'b0};
    assign shift_mag = shift2n[NW] ? (~shift2n + 1'b1) : shift2n;
    assign shifted   = shift2n[NW] ? (q_corrected <<< shift_mag)   // N<0 -> лево
                                    : (q_corrected >>> shift_mag);  // N>=0 -> право, как и у R

    logic signed [W_INT-1:0] dropped_lo;
    assign dropped_lo = shifted >>> GUARD_LO; // убираем нижний guard, точка встаёт как в Q16.16+GUARD_HI

    logic signed [W_Q16-1:0] final_saturated;
    always_comb begin
        if (dropped_lo[W_INT-GUARD_LO-1 : W_Q16-1] != {(GUARD_HI+1){dropped_lo[W_Q16-1]}}) begin
            final_saturated = dropped_lo[W_INT-GUARD_LO-1] ? {1'b1, {(W_Q16-1){1'b0}}}
                                                            : {1'b0, {(W_Q16-1){1'b1}}};
        end else begin
            final_saturated = dropped_lo[W_Q16-1:0];
        end
    end

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            inv_r_result <= '0;
            local_id_out <= '0;
            out_valid    <= 1'b0;
        end else begin
            inv_r_result <= final_saturated;
            local_id_out <= local_id;
            out_valid    <= in_valid;
        end
    end

endmodule