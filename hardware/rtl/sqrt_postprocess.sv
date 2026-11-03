module sqrt_postprocess #(
    parameter int W_INT    = 41,   // тракт CORDIC (32 + GUARD_HI + GUARD_LO)
    parameter int W_Q16    = 32,   // финальный формат, как весь остальной массив
    parameter int GUARD_HI = 4,
    parameter int GUARD_LO = 5,
    parameter int NW       = 6
)(
    input  logic                    clk,
    input  logic                    rst_n,

    input  logic signed [W_INT-1:0] x_out_k,     // сырой K_h*sqrt(w_norm), из hyperbolic_cordic_sqrt
    input  logic signed [NW-1:0]    shift_n,     // N из w_normalize, тот же, что был применён ко входу
    input  logic         [3:0]      local_id,
    input  logic                    in_valid,

    output logic signed [W_Q16-1:0] sqrt_result, // готовый sqrt(w) в Q16.16
    output logic         [3:0]      local_id_out,
    output logic                    out_valid
);

    // ==================== Стадия A: компенсация K_h (CSD, сдвиги+сложения) ====================
    // 0.828159360992 * 65536 = 54275 (округление)
    // CSD: 54275 = 2^16 - 2^14 + 2^12 + 2^10 + 2^2 - 2^0  (проверено арифметически)
    // Значение не меняется с переходом на 22 итерации — вклад i>~15 ниже разрешения формата.
    localparam int GAIN_EXT_W = W_INT + 17; // запас под <<<16 без потери бит

    logic signed [GAIN_EXT_W-1:0] gain_x_ext;
    logic signed [GAIN_EXT_W-1:0] gain_sum;
    logic signed [GAIN_EXT_W-1:0] gain_shifted;
    logic signed [W_INT-1:0]      gain_saturated;

    assign gain_x_ext = GAIN_EXT_W'(x_out_k);

    assign gain_sum = (gain_x_ext <<< 16)
                     - (gain_x_ext <<< 14)
                     + (gain_x_ext <<< 12)
                     + (gain_x_ext <<< 10)
                     + (gain_x_ext <<< 2)
                     - gain_x_ext;

    assign gain_shifted = gain_sum >>> 16;

    always_comb begin
        if (gain_shifted[GAIN_EXT_W-1:W_INT-1] != {(GAIN_EXT_W-W_INT+1){gain_shifted[W_INT-1]}}) begin
            gain_saturated = gain_shifted[GAIN_EXT_W-1] ? {1'b1, {(W_INT-1){1'b0}}}
                                                         : {1'b0, {(W_INT-1){1'b1}}};
        end else begin
            gain_saturated = gain_shifted[W_INT-1:0];
        end
    end

    logic signed [W_INT-1:0] stageA_reg;
    logic signed [NW-1:0]    n_reg_a;
    logic         [3:0]      id_reg_a;
    logic                    v_reg_a;

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            stageA_reg <= '0;
            n_reg_a    <= '0;
            id_reg_a   <= '0;
            v_reg_a    <= 1'b0;
        end else begin
            stageA_reg <= gain_saturated;       // теперь это настоящий sqrt(w_norm)
            n_reg_a    <= shift_n;               // транзит
            id_reg_a   <= local_id;              // транзит
            v_reg_a    <= in_valid;
        end
    end

    // ==================== Стадия B: сдвиг обратно на N + возврат в Q16.16 ====================
    // sqrt(w) = sqrt(w_norm * 4^N) = sqrt(w_norm) * 2^N
    // N>=0 -> исходный w был большим, w_normalize сдвигал вправо на 2N -> тут сдвигаем ВЛЕВО на N
    // N<0  -> исходный w был маленьким, w_normalize сдвигал влево  -> тут сдвигаем ВПРАВО на |N|
    logic [$clog2(W_INT)-1:0] shift_mag_b;
    logic signed [W_INT-1:0]  shifted_b;

    assign shift_mag_b = n_reg_a[NW-1] ? (~n_reg_a + 1'b1) : n_reg_a;
    assign shifted_b   = n_reg_a[NW-1] ? (stageA_reg >>> shift_mag_b)
                                        : (stageA_reg <<< shift_mag_b);

    // Убираем GUARD_LO (сдвиг точки обратно) и проверяем переполнение GUARD_HI
    logic signed [W_INT-1:0]  dropped_lo; // ещё W_INT бит, но точка уже как в Q16.16 + GUARD_HI
    assign dropped_lo = shifted_b >>> GUARD_LO;

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
            sqrt_result  <= '0;
            local_id_out <= '0;
            out_valid    <= 1'b0;
        end else begin
            sqrt_result  <= final_saturated;
            local_id_out <= id_reg_a;   // транзит, последний раз
            out_valid    <= v_reg_a;
        end
    end

endmodule
