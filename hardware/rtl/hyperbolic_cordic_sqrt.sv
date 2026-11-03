module hyperbolic_cordic_sqrt #(
    parameter int W_INT = 41,   // тот же тракт, что и w_normalize (32 Q16.16 + 4 + 5 guard)
    parameter int AW    = W_INT,
    parameter int NW    = 6,    // разрядность shift_n, как в w_normalize
    parameter int N     = 22    // итераций — снижено благодаря range-reduction на входе
)(
    input  logic                    clk,
    input  logic                    rst_n,

    // Вход уже нормализован в [0.5, 2.0) модулем w_normalize
    input  logic signed [W_INT-1:0] w_norm,
    input  logic signed [NW-1:0]    shift_n,   // протаскиваем насквозь, применяется в конце
    input  logic         [3:0]      local_id,  // номер потока, тоже просто транзит
    input  logic                    in_valid,

    // Сырой результат: K_h * sqrt(w_norm), гейн ещё не скомпенсирован, сдвиг ещё не отыгран
    output logic signed [W_INT-1:0] x_out_k,
    output logic signed [W_INT-1:0] y_out_k,
    output logic signed [AW-1:0]    angle_out, // не используется
    output logic signed [NW-1:0]    shift_n_out, // тот же shift_n, но с задержкой всего пайплайна
    output logic         [3:0]      local_id_out,
    output logic                    out_valid
);

    // ---- Стадия 0: w_norm +- 1/4 ----
    // 0.25 в этом формате: точка после бита (16+GUARD_LO-1); раз GUARD_LO зашит в W_INT
    // через параметры вызывающей стороны (w_normalize), тут проще выразить через сам W_INT:
    // формат идентичен w_normalize, так что переиспользуем ту же арифметику константы.
    localparam int GUARD_LO_ASSUMED = W_INT - 32 - 4; // см. w_normalize (GUARD_HI=4 по умолчанию)
    localparam logic signed [W_INT-1:0] QUARTER = W_INT'(1) <<< (14 + GUARD_LO_ASSUMED);

    logic signed [W_INT-1:0] x0_reg, y0_reg;
    logic signed [NW-1:0]    n0_reg;
    logic         [3:0]      id0_reg;
    logic                    v0_reg;

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            x0_reg  <= '0;
            y0_reg  <= '0;
            n0_reg  <= '0;
            id0_reg <= '0;
            v0_reg  <= 1'b0;
        end else begin
            x0_reg  <= w_norm + QUARTER;
            y0_reg  <= w_norm - QUARTER;
            n0_reg  <= shift_n;
            id0_reg <= local_id;
            v0_reg  <= in_valid;
        end
    end

    // ---- LUT atanh(2^-i), i=1..22 (тот же масштаб Q.16, что и раньше) ----
    // Функция с case вместо indexed array-literal localparam — Icarus/iverilog
    // не элаборирует '{1: ..., ...} синтаксис (established gotcha).
    function automatic logic signed [AW-1:0] atanh_lut(input int iter);
        case (iter)
            1:  atanh_lut = AW'(19'sd36000);
            2:  atanh_lut = AW'(19'sd16739);
            3:  atanh_lut = AW'(19'sd8235);
            4:  atanh_lut = AW'(19'sd4101);
            5:  atanh_lut = AW'(19'sd2049);
            6:  atanh_lut = AW'(19'sd1024);
            7:  atanh_lut = AW'(19'sd512);
            8:  atanh_lut = AW'(19'sd256);
            9:  atanh_lut = AW'(19'sd128);
            10: atanh_lut = AW'(19'sd64);
            11: atanh_lut = AW'(19'sd32);
            12: atanh_lut = AW'(19'sd16);
            13: atanh_lut = AW'(19'sd8);
            14: atanh_lut = AW'(19'sd4);
            15: atanh_lut = AW'(19'sd2);
            16: atanh_lut = AW'(19'sd1);
            default: atanh_lut = '0; // i>=17 ниже разрешения LUT — безобидно, angle_out не используется
        endcase
    endfunction

    // ---- Повторы на i=4, i=13 (оба всё ещё в диапазоне 1..22) ----
    localparam int PIPE_DEPTH = N + 2; // 22 + 2 = 24 стадии

    // Снова через функцию с case, не через positional array-literal localparam —
    // тот же Icarus-gotcha, что и с LUT выше.
    function automatic int iter_seq(input int k);
        case (k)
            0: iter_seq=1;  1: iter_seq=2;  2: iter_seq=3;  3: iter_seq=4;
            4: iter_seq=4;  5: iter_seq=5;  6: iter_seq=6;  7: iter_seq=7;
            8: iter_seq=8;  9: iter_seq=9;  10: iter_seq=10; 11: iter_seq=11;
            12: iter_seq=12; 13: iter_seq=13; 14: iter_seq=13; 15: iter_seq=14;
            16: iter_seq=15; 17: iter_seq=16; 18: iter_seq=17; 19: iter_seq=18;
            20: iter_seq=19; 21: iter_seq=20; 22: iter_seq=21; 23: iter_seq=22;
            default: iter_seq = 0;
        endcase
    endfunction

    logic signed [W_INT-1:0] x [0:PIPE_DEPTH];
    logic signed [W_INT-1:0] y [0:PIPE_DEPTH];
    logic signed [AW-1:0]    z [0:PIPE_DEPTH];
    logic signed [NW-1:0]    ndl [0:PIPE_DEPTH]; // delay-line для shift_n
    logic         [3:0]      idl [0:PIPE_DEPTH]; // delay-line для local_id
    logic                    v [0:PIPE_DEPTH];

    always_comb begin
        x[0]   = x0_reg;
        y[0]   = y0_reg;
        z[0]   = '0;
        ndl[0] = n0_reg;
        idl[0] = id0_reg;
        v[0]   = v0_reg;
    end

    genvar k;
    generate
        for (k = 0; k < PIPE_DEPTH; k++) begin : hyp_stage
            localparam int ITER = iter_seq(k);

            always_ff @(posedge clk) begin
                if (!rst_n) begin
                    x[k+1]   <= '0;
                    y[k+1]   <= '0;
                    z[k+1]   <= '0;
                    ndl[k+1] <= '0;
                    idl[k+1] <= '0;
                    v[k+1]   <= 1'b0;
                end else begin
                    if (y[k] >= 0) begin
                        x[k+1] <= x[k] - (y[k] >>> ITER);
                        y[k+1] <= y[k] - (x[k] >>> ITER);
                        z[k+1] <= z[k] + atanh_lut(ITER);
                    end else begin
                        x[k+1] <= x[k] + (y[k] >>> ITER);
                        y[k+1] <= y[k] + (x[k] >>> ITER);
                        z[k+1] <= z[k] - atanh_lut(ITER);
                    end
                    ndl[k+1] <= ndl[k]; // shift_n просто едет транзитом, ни на что не влияя
                    idl[k+1] <= idl[k]; // local_id тоже
                    v[k+1]   <= v[k];
                end
            end
        end
    endgenerate

    assign x_out_k      = x[PIPE_DEPTH];
    assign y_out_k       = y[PIPE_DEPTH];
    assign angle_out     = z[PIPE_DEPTH];
    assign shift_n_out   = ndl[PIPE_DEPTH];
    assign local_id_out  = idl[PIPE_DEPTH];
    assign out_valid     = v[PIPE_DEPTH];

endmodule