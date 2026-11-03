module pe_input_mux (
    input  logic               clk,
    input  logic               rst_n,

    // Один фрейм = одно значение за такт этого модуля.
    // Разбор быстрой шины (DDR-приём, гребёнка 2:1) — в отдельном модуле,
    // сюда данные приходят уже как обычный поток "один операнд за такт".
    input  logic signed [31:0] local_data,
    input  logic               sub,          // sum1 - sum2 вместо sum1 + sum2

    // --- Управление: уже расшифрованные разрешения от cmd_parser ---
    input  logic signed [31:0] in_a,
    input  logic signed [31:0] in_b,
    input  logic         [1:0] sel,

    input  logic         [4:0] in_id,
    input  logic               compare_id,

    // cmd_parser сам знает, когда обе половины (mux1, mux2) готовы к выдаче в MAC
    input  logic               issue_vld,

    output logic signed [31:0] a_out,        // -> mac in_a (mux1)
    output logic signed [31:0] b_out,        // -> mac in_b (mux2)
    output logic         [4:0] out_id,
    output logic               out_vld
);

    // --- Регистры-приёмники: держат значение, пока их явно не перезапишут ---
    logic signed [31:0] sum1_reg, sum2_reg;
    logic signed [31:0] mux1_reg, mux2_reg;

    logic        [4:0]  local_id_sum;
    logic        [4:0]  local_id_mux;

    logic signed [32:0] sum_ext;
    logic signed [31:0] sum_saturated;

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            sum1_reg      <= '0;
            sum2_reg      <= '0;
            mux1_reg      <= '0;
            mux2_reg      <= '0;
            local_id_mux  <= '0;
        end else begin
            if (sel == 2'b01) begin
                sum1_reg <= in_a;
                sum2_reg <= in_b;
            end

            // mux1 — "прямой" операнд умножителя. Он нужен не только при sel=00
            // (прямая передача), но и при sel=10 (операнд C составной операции
            // (A±B)*C приходит на in_a в этом же такте) и при sel=11 (операнд,
            // который умножается на константу из локального буфера). Только при
            // sel=01 (такт накопления суммы) mux1 не трогаем — в этом такте
            // умножитель ещё не используется, копится sum1/sum2.
            if (sel == 2'b00 || sel == 2'b10 || sel == 2'b11) begin
                mux1_reg     <= in_a;
                local_id_mux <= in_id;
            end

            case (sel)
                2'b00:  mux2_reg <= in_b;
                2'b10:  mux2_reg <= sum_saturated;
                2'b11:  mux2_reg <= local_data;
                default: ;
            endcase
        end
    end

    // Пресумматор: sum1_reg и sum2_reg — 32-битные регистры, но сумма/разность
    // двух 32-битных чисел со знаком может на 1 бит не влезть в 32 бита (напр.,
    // max+max). Расширяем оба операнда до 33 бит ЗНАКОВО перед +/-, чтобы
    // результат заведомо не переполнился внутри sum_ext — тогда переполнение
    // относительно целевых 32 бит надёжно детектируется простым сравнением
    // sum_ext[32] (знак после операции) с sum_ext[31] (знак в границах 32 бит)
    // ниже, без риска получить "ложное" переполнение из-за нехватки разрядности
    // самого sum_ext. Операторы "+"/"-" применены к векторам (не к классам и
    // не к константам, требующим свёртки) — для такой пары операндов Genus
    // детерминированно отображает их в комбинационный сумматор/вычитатель
    // нужной разрядности, без неоднозначности разбора (в отличие, например,
    // от "*", который может лечь на разные аппаратные примитивы в зависимости
    // от библиотеки — см. обоснование в mac_q16).
    assign sum_ext = sub ? (33'(sum1_reg) - 33'(sum2_reg))
                          : (33'(sum1_reg) + 33'(sum2_reg));

    always_comb begin
        if (sum_ext[32] != sum_ext[31]) begin
            sum_saturated = sum_ext[32] ? 32'sh8000_0000 : 32'sh7FFF_FFFF;
        end else begin
            sum_saturated = sum_ext[31:0];
        end
    end

    // --- Выход в MAC: без своей логики валида — транслируем issue_vld ---
    // out_id обновляется только при реальной выдаче (issue_vld=1), во всех
    // остальных тактах держит предыдущее значение — это намеренно (см. текст
    // отчёта, п. "Чему равен out_id при issue_vld=0"). Явный сброс в '0 задаёт
    // определённое начальное значение до первой выдачи; потребитель всё равно
    // обязан смотреть на out_vld, а не читать out_id "просто так".
    always_ff @(posedge clk) begin
        if (!rst_n) begin
            out_vld <= 1'b0;
            a_out   <= '0;
            b_out   <= '0;
            out_id  <= '0;
        end else begin
            out_vld <= issue_vld;
            a_out   <= mux1_reg;
            b_out   <= mux2_reg;
            if (issue_vld) begin
                out_id <= local_id_mux;
            end
        end
    end

endmodule
