`timescale 1ns / 1ps

`timescale 1ns / 1ps

module mac_q16 #(
    parameter int PIPELINE_STAGES = 4
) (
    input  logic               clk,
    input  logic               rst_n,
    input  logic               in_vld,
    input  logic               sel,        // Добавленный входной сигнал
    input  logic signed [31:0] in_a,
    input  logic signed [31:0] in_b,
    input  logic        [3:0]  in_id,      // ID транзакции, едет рядом с данными
    output logic               out_vld,
    output logic               out_sel,    // Добавленный выходной сигнал
    output logic signed [31:0] out_res,
    output logic        [3:0]  out_id,     // ID, выровненный с out_res
    output logic               busy
);

    // Умножение без маскирования — просто летит в конвейер
    logic signed [63:0] mult_comb;
    assign mult_comb = in_a * in_b;

    // --- Pipeline registers ---
    logic signed [63:0] pipe [0:PIPELINE_STAGES-1];
    logic               vld_pipe [0:PIPELINE_STAGES-1];
    logic               sel_pipe [0:PIPELINE_STAGES-1]; // Конвейер для сигнала sel
    logic        [3:0]  id_pipe  [0:PIPELINE_STAGES-1]; // Конвейер ID, без сброса, как данные

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            // Сбрасываем ТОЛЬКО валидность. Регистры данных не имеют сброса
            for (int i = 0; i < PIPELINE_STAGES; i++) begin
                vld_pipe[i] <= 1'b0;
                sel_pipe[i] <= 1'b0; // Сброс конвейера sel
            end
        end else begin
            vld_pipe[0] <= in_vld;
            sel_pipe[0] <= sel; // Запись входного sel в первый триггер
            for (int i = 1; i < PIPELINE_STAGES; i++) begin
                vld_pipe[i] <= vld_pipe[i-1];
                sel_pipe[i] <= sel_pipe[i-1]; // Продвижение по конвейеру
            end
        end

        // Данные просто через трубу каждый такт
        pipe[0]    <= mult_comb;
        id_pipe[0] <= in_id;
        for (int i = 1; i < PIPELINE_STAGES; i++) begin
            pipe[i]    <= pipe[i-1];
            id_pipe[i] <= id_pipe[i-1];
        end
    end

    // --- Banker's rounding ---
    logic signed [63:0] last_pipe;
    assign last_pipe = pipe[PIPELINE_STAGES-1];

    logic        guard;  
    logic        lsb;    
    logic        sticky; 
    logic        round;  

    assign guard  = last_pipe[15];
    assign lsb    = last_pipe[16];
    assign sticky = |last_pipe[14:0];
    assign round  = guard & (sticky | lsb);

    // --- Безопасное сложение и сатурация ---
    // Расширяем результат до 49 бит, чтобы корректно поймать овефлоу после округления
    logic signed [48:0] ext_result;
    assign ext_result = $signed(last_pipe[63:16]) + $signed({48'b0, round});

    // Знак берем строго из старшего бита 64-битного результата
    logic sign_bit;
    assign sign_bit = last_pipe[63];

    // Проверка переполнения: 
    // Если старшие биты результата не равны знаковому расширению 31-го бита
    logic overflow;
    assign overflow = (ext_result[48:31] != {18{ext_result[31]}});

    always_comb begin
        if (overflow) begin
            out_res = sign_bit ? 32'sh8000_0000 : 32'sh7FFF_FFFF;
        end else begin
            out_res = ext_result[31:0];
        end
    end

    // --- Outputs ---
    assign out_vld = vld_pipe[PIPELINE_STAGES-1];
    assign out_sel = sel_pipe[PIPELINE_STAGES-1]; // Вывод задержанного сигнала sel
    assign out_id  = id_pipe[PIPELINE_STAGES-1];

    always_comb begin
        busy = in_vld;
        for (int i = 0; i < PIPELINE_STAGES; i++)
            busy = busy || vld_pipe[i];
    end

endmodule






































































































/*module mac_q16 #(
    parameter int PIPELINE_STAGES = 4
) (
    input  logic               clk,
    input  logic               rst_n,
    input  logic               in_vld,
    input  logic signed [31:0] in_a,
    input  logic signed [31:0] in_b,
    output logic               out_vld,
    output logic signed [31:0] out_res,
    output logic               busy
);

    // Умножение без маскирования — просто летит в конвейер
    logic signed [63:0] mult_comb;
    assign mult_comb = in_a * in_b;

    // --- Pipeline registers ---
    logic signed [63:0] pipe [0:PIPELINE_STAGES-1];
    logic               vld_pipe [0:PIPELINE_STAGES-1];

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            // Сбрасываем ТОЛЬКО валидность. Регистры данных не имеют сброса
            for (int i = 0; i < PIPELINE_STAGES; i++) begin
                vld_pipe[i] <= 1'b0;
            end
        end else begin
            vld_pipe[0] <= in_vld;
            for (int i = 1; i < PIPELINE_STAGES; i++) begin
                vld_pipe[i] <= vld_pipe[i-1];
            end
        end

        // Данные просто текут по трубе каждый такт
        pipe[0] <= mult_comb;
        for (int i = 1; i < PIPELINE_STAGES; i++) begin
            pipe[i] <= pipe[i-1];
        end
    end

    // --- Banker's rounding ---
    logic signed [63:0] last_pipe;
    assign last_pipe = pipe[PIPELINE_STAGES-1];

    logic        guard;  
    logic        lsb;    
    logic        sticky; 
    logic        round;  

    assign guard  = last_pipe[15];
    assign lsb    = last_pipe[16];
    assign sticky = |last_pipe[14:0];
    assign round  = guard & (sticky | lsb);

    // --- Безопасное сложение и сатурация ---
    // Расширяем результат до 49 бит, чтобы корректно поймать овефлоу после округления
    logic signed [48:0] ext_result;
    assign ext_result = $signed(last_pipe[63:16]) + $signed({48'b0, round});

    // Знак берем строго из старшего бита 64-битного результата
    logic sign_bit;
    assign sign_bit = last_pipe[63];

    // Проверка переполнения: 
    // Если старшие биты результата не равны знаковому расширению 31-го бита
    logic overflow;
    assign overflow = (ext_result[48:31] != {18{ext_result[31]}});

    always_comb begin
        if (overflow) begin
            out_res = sign_bit ? 32'sh8000_0000 : 32'sh7FFF_FFFF;
        end else begin
            out_res = ext_result[31:0];
        end
    end

    // --- Outputs ---
    assign out_vld = vld_pipe[PIPELINE_STAGES-1];

    always_comb begin
        busy = in_vld;
        for (int i = 0; i < PIPELINE_STAGES; i++)
            busy = busy || vld_pipe[i];
    end

endmodule*/






