module linear_cordic_div #(
    parameter int W_INT    = 41,
    parameter int GUARD_LO = 5,
    parameter int AW       = W_INT,  // z-аккумулятор ЗДЕСЬ — реальный результат (1/R), не отбрасываем
    parameter int NW       = 6,
    parameter int N        = 22      // та же глубина, что и у sqrt-ядра, для единообразной латентности
)(
    input  logic                    clk,
    input  logic                    rst_n,

    input  logic signed [W_INT-1:0] r_norm,    // из w_normalize, применённого к R (результату sqrt)
    input  logic signed [NW-1:0]    shift_r,
    input  logic         [3:0]      local_id,
    input  logic                    in_valid,

    output logic signed [AW-1:0]    q_out,      // 1/r_norm, ещё не отмасштабировано обратно
    output logic signed [NW-1:0]    shift_r_out,
    output logic         [3:0]      local_id_out,
    output logic                    doubled_out, // если 1 — div_postprocess должен удвоить результат
    output logic                    out_valid
);

    // ---- LUT 2^-i в формате Q(16+GUARD_LO), точные степени двойки, кроме последней ----
    // Точка на бите (16+GUARD_LO); при GUARD_LO=5 это 21. Последняя (i=22) итерация
    // формально даёт 0.5 в этом масштабе — округлено до 1. Ошибка на этом шаге —
    // не более 0.5 младшего разряда РАСШИРЕННОГО формата, что ниже финального порога
    // отбрасывания GUARD-бит в постобработке, так что безобидно.
    localparam int POINT = 16 + GUARD_LO;

    // Функция с case вместо indexed array-literal localparam — Icarus/iverilog
    // не элаборирует '{1: ..., 2: ..., ...} синтаксис (established gotcha, см.
    // тот же приём в ATANH_LUT, hyperbolic_cordic_sqrt.sv).
    function automatic logic signed [AW-1:0] lin_lut(input int iter);
        case (iter)
            1:  lin_lut = AW'(1 <<< (POINT-1));
            2:  lin_lut = AW'(1 <<< (POINT-2));
            3:  lin_lut = AW'(1 <<< (POINT-3));
            4:  lin_lut = AW'(1 <<< (POINT-4));
            5:  lin_lut = AW'(1 <<< (POINT-5));
            6:  lin_lut = AW'(1 <<< (POINT-6));
            7:  lin_lut = AW'(1 <<< (POINT-7));
            8:  lin_lut = AW'(1 <<< (POINT-8));
            9:  lin_lut = AW'(1 <<< (POINT-9));
            10: lin_lut = AW'(1 <<< (POINT-10));
            11: lin_lut = AW'(1 <<< (POINT-11));
            12: lin_lut = AW'(1 <<< (POINT-12));
            13: lin_lut = AW'(1 <<< (POINT-13));
            14: lin_lut = AW'(1 <<< (POINT-14));
            15: lin_lut = AW'(1 <<< (POINT-15));
            16: lin_lut = AW'(1 <<< (POINT-16));
            17: lin_lut = AW'(1 <<< (POINT-17));
            18: lin_lut = AW'(1 <<< (POINT-18));
            19: lin_lut = AW'(1 <<< (POINT-19));
            20: lin_lut = AW'(1 <<< (POINT-20));
            21: lin_lut = AW'(1 <<< (POINT-21));
            22: lin_lut = AW'(1); // exponent -1 -> 0.5, округлено вверх
            default: lin_lut = '0;
        endcase
    endfunction

    // ---- Стадия 0: x0=r_norm (знаменатель), y0=1.0 (числитель), z0=0 ----
    // ВАЖНО: linear-mode CORDIC сходится к правильному частному только при
    // |y0/x0| <= 1. Раз y0=1.0 фиксирован, для r_norm<1.0 (частное>1) алгоритм
    // не сходится — y никогда не меняет знак, z монотонно растёт и упирается
    // в потолок ~1.0 вместо истинного ответа. Обнаружено тестированием.
    // Фикс: если r_norm<1.0, удваиваем x0 перед итерацией (гарантированно
    // приводит к сходящемуся случаю |y0/x0|<=1), а на выходе результат нужно
    // удвоить обратно: 1/r_norm = 2*(1/(2*r_norm)). Флаг `doubled` едет
    // транзитом до div_postprocess, где и применяется обратное удвоение.
    localparam logic signed [W_INT-1:0] ONE_Q = W_INT'(1 <<< POINT);

    logic signed [W_INT-1:0] x0_reg, y0_reg;
    logic signed [NW-1:0]    n0_reg;
    logic         [3:0]      id0_reg;
    logic                    dbl0_reg;
    logic                    v0_reg;

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            x0_reg <= '0; y0_reg <= '0; n0_reg <= '0; id0_reg <= '0;
            dbl0_reg <= 1'b0; v0_reg <= 1'b0;
        end else begin
            dbl0_reg <= (r_norm < ONE_Q);
            x0_reg  <= (r_norm < ONE_Q) ? (r_norm <<< 1) : r_norm;
            y0_reg  <= ONE_Q;
            n0_reg  <= shift_r;
            id0_reg <= local_id;
            v0_reg  <= in_valid;
        end
    end

    // ---- Пайплайн: x НЕ меняется ни на одной стадии (свойство linear-mode) ----
    logic signed [W_INT-1:0] x [0:N];
    logic signed [W_INT-1:0] y [0:N];
    logic signed [AW-1:0]    z [0:N];
    logic signed [NW-1:0]    ndl [0:N];
    logic         [3:0]      idl [0:N];
    logic                    dbl [0:N];
    logic                    v [0:N];

    always_comb begin
        x[0]   = x0_reg;
        y[0]   = y0_reg;
        z[0]   = '0;
        ndl[0] = n0_reg;
        idl[0] = id0_reg;
        dbl[0] = dbl0_reg;
        v[0]   = v0_reg;
    end

    genvar k;
    generate
        for (k = 0; k < N; k++) begin : lin_stage
            localparam int ITER = k + 1; // без повторов, 1..N по порядку

            always_ff @(posedge clk) begin
                if (!rst_n) begin
                    x[k+1] <= '0; y[k+1] <= '0; z[k+1] <= '0;
                    ndl[k+1] <= '0; idl[k+1] <= '0; dbl[k+1] <= 1'b0; v[k+1] <= 1'b0;
                end else begin
                    x[k+1] <= x[k]; // не меняется — определяющее свойство linear-mode
                    if (y[k] >= 0) begin
                        y[k+1] <= y[k] - (x[k] >>> ITER);
                        z[k+1] <= z[k] + lin_lut(ITER);
                    end else begin
                        y[k+1] <= y[k] + (x[k] >>> ITER);
                        z[k+1] <= z[k] - lin_lut(ITER);
                    end
                    ndl[k+1] <= ndl[k];
                    idl[k+1] <= idl[k];
                    dbl[k+1] <= dbl[k];
                    v[k+1]   <= v[k];
                end
            end
        end
    endgenerate

    assign q_out        = z[N];
    assign shift_r_out  = ndl[N];
    assign local_id_out = idl[N];
    assign doubled_out  = dbl[N];
    assign out_valid    = v[N];

endmodule