module hyperbolic_cordic_vectoring #(
    parameter int W_INT = 18,   // разрядность x/y (тот же тракт, что и у circular-варианта)
    parameter int AW    = 19    // разрядность "угла" z (тут — вспомогательное накопление, не угол)
)(
    input  logic                  clk,
    input  logic                  rst,

    // Подготовка входов — забота вызывающей стороны:
    //   x_in = w + 1/4
    //   y_in = w - 1/4
    // тогда x_out_k -> K_h * sqrt(w), а не что-то отвлечённое.
    // Приведение к четверти/октанту тут НЕ нужно — это не угол, а просто разность квадратов.
    input  logic signed [W_INT-1:0]   x_in,
    input  logic signed [W_INT-1:0]   y_in,
    input  logic                  in_valid,

    output logic signed [W_INT-1:0]   x_out_k,   // K_h * sqrt(w), гейн ещё не скомпенсирован
    output logic signed [W_INT-1:0]   y_out_k,   // должен сойтись к ~0
    output logic signed [AW-1:0]  angle_out,     // не используется для sqrt, оставлен для общности
    output logic                  out_valid
);

    // ---- LUT atanh(2^-i), i=1..16, масштаб Q.16 (тот же, что и atan_lut в circular-варианте) ----
    // localparam, а не initial — гарантированно синтезируется как константа/ROM, initial для этого
    // на ASIC-синтезе (в отличие от FPGA) не гарантирован.
    localparam int N = 16;
    localparam logic signed [AW-1:0] ATANH_LUT [1:N] = '{
        1:  19'sd35999,
        2:  19'sd16739,
        3:  19'sd8235,
        4:  19'sd4101,
        5:  19'sd2049,
        6:  19'sd1024,
        7:  19'sd512,
        8:  19'sd256,
        9:  19'sd128,
        10: 19'sd64,
        11: 19'sd32,
        12: 19'sd16,
        13: 19'sd8,
        14: 19'sd4,
        15: 19'sd2,
        16: 19'sd1
    };
    // Значения — первый расчёт, не сверенные скриптом с высокой точностью.
    // Если после интеграции точность нормализации не устроит — пересчитать и заменить,
    // структура пайплайна от этого не меняется.

    // ---- Расписание итераций: hyperbolic CORDIC для сходимости требует повторов
    //      на i = 4, 13, 40, 121... (только 4 и 13 попадают в диапазон 1..16) ----
    localparam int PIPE_DEPTH = N + 2; // 16 итераций + 2 повтора (i=4, i=13)
    localparam int ITER_SEQ [0:PIPE_DEPTH-1] = '{
        1, 2, 3, 4, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 13, 14, 15, 16
    };

    logic signed [W_INT-1:0] x [0:PIPE_DEPTH];
    logic signed [W_INT-1:0] y [0:PIPE_DEPTH];
    logic signed [AW-1:0]    z [0:PIPE_DEPTH];
    logic                    v [0:PIPE_DEPTH];

    assign x[0] = x_in;
    assign y[0] = y_in;
    assign z[0] = '0;
    assign v[0] = in_valid;

    genvar k;
    generate
        for (k = 0; k < PIPE_DEPTH; k++) begin : hyp_stage
            localparam int ITER = ITER_SEQ[k]; // фактический номер итерации на этой физической стадии

            always_ff @(posedge clk) begin
                if (!rst) begin
                    x[k+1] <= '0;
                    y[k+1] <= '0;
                    z[k+1] <= '0;
                    v[k+1] <= 1'b0;
                end else begin
                    // Гиперболическая итерация: в отличие от circular, оба кросс-члена
                    // (x-обновление и y-обновление) имеют ОДИНАКОВЫЙ знак, а не противоположный.
                    if (y[k] > 0) begin
                        x[k+1] <= x[k] + (y[k] >>> ITER);
                        y[k+1] <= y[k] + (x[k] >>> ITER);
                        z[k+1] <= z[k] + ATANH_LUT[ITER];
                    end else if (y[k] < 0) begin
                        x[k+1] <= x[k] - (y[k] >>> ITER);
                        y[k+1] <= y[k] - (x[k] >>> ITER);
                        z[k+1] <= z[k] - ATANH_LUT[ITER];
                    end else begin
                        x[k+1] <= x[k];
                        y[k+1] <= y[k];
                        z[k+1] <= z[k];
                    end
                    v[k+1] <= v[k];
                end
            end
        end
    endgenerate

    assign x_out_k   = x[PIPE_DEPTH];
    assign y_out_k   = y[PIPE_DEPTH];
    assign angle_out = z[PIPE_DEPTH];
    assign out_valid = v[PIPE_DEPTH];

endmodule
