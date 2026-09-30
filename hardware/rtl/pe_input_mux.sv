`timescale 1ns / 1ps

module pe_input_mux (
    input  logic               clk,
    input  logic               rst_n,

    // Один фрейм = одно значение за такт этого модуля.
    // Разбор быстрой шины (clk800 -> clk400, DDR gearbox) — в отдельном модуле,
    // сюда данные приходят уже как обычный поток "один frame за такт".
    input  logic signed [31:0] local_data,
    input  logic               sub,          // sum1 - sum2 вместо sum1 + sum2 (действует в такте sel=10)

    // --- Управление: уже расшифрованные разрешения от командного парсера ---
    // Парсер сам решает, сколько тактов копить, эта модуль только исполняет.
    input  logic signed [31:0] in_a,      // frame_data -> sum1_reg
    input  logic signed [31:0] in_b,      // frame_data -> sum2_reg
    input  logic        [1:0]  sel,

    input  logic        [3:0]  in_id,

    // Парсер сам знает, когда обе половины (mux1, mux2) готовы к выдаче в MAC.
    // Команда для MAC подаётся вместе с issue_vld и едет рядом с out_vld.
    input  logic               issue_vld,
    input  logic               issue_sel,

    output logic signed [31:0] a_out,        // -> mac in_a (mux1)
    output logic signed [31:0] b_out,        // -> mac in_b (mux2)
    output logic        [3:0]  out_id,       // -> mac in_id
    output logic               out_vld,      // -> mac in_vld
    output logic               out_sel       // -> mac sel
);

    // --- Регистры-приёмники: держат значение, пока их явно не перезапишут ---
    logic signed [31:0] sum1_reg, sum2_reg;
    logic signed [31:0] mux1_reg, mux2_reg;

    logic        [3:0]  local_id_mux;

    logic signed [32:0] sum_ext;
    logic signed [31:0] sum_saturated;

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            sum1_reg      <= '0;
            sum2_reg      <= '0;
            mux1_reg      <= '0;
            mux2_reg      <= '0;
        end else begin
            if (sel == 2'b01) begin
                sum1_reg <= in_a; // Кладем из входного регистра А
                sum2_reg <= in_b; // Кладем из входного регистра Б
            end

            case (sel)
                2'b00, 2'b10, 2'b11: begin
                    mux1_reg     <= in_a;
                    local_id_mux <= in_id;
                end
                default: ; // При sel = 2'b01 ничего не меняем в mux1
            endcase

            case (sel)
                2'b00:  mux2_reg <= in_b;
                2'b10:  mux2_reg <= sum_saturated;
                2'b11:  mux2_reg <= local_data;
                default: ;
            endcase
        end
    end


    assign sum_ext = sub ? (33'(sum1_reg) - 33'(sum2_reg))
                          : (33'(sum1_reg) + 33'(sum2_reg));

    always_comb begin
        if (sum_ext[32] != sum_ext[31]) begin
            sum_saturated = sum_ext[32] ? 32'sh8000_0000 : 32'sh7FFF_FFFF;
        end else begin
            sum_saturated = sum_ext[31:0];
        end
    end

    // --- Выход в MAC: тупо, без своей логики валида — просто транслируем issue_vld ---
    always_ff @(posedge clk) begin
        if (!rst_n) begin
            out_vld <= 1'b0;
            out_sel <= 1'b0;
        end else begin
            out_vld <= issue_vld;
            out_sel <= issue_sel;
            a_out <= mux1_reg;
            b_out <= mux2_reg;
            if (issue_vld) begin
                out_id <= local_id_mux;
            end
        end
    end

endmodule


































































// module pe_input_mux (
//     input  logic               clk,
//     input  logic               rst_n,
//     input  logic               in_vld,
//     input  logic signed [31:0] x,
//     input  logic signed [31:0] y,
//     input  logic signed [31:0] b,
//     input  logic               sel,
//     input  logic               sub,
//     input  logic               sel_out_v, // Новый транзитный входной сигнал

//     output logic signed [31:0] a_out,
//     output logic signed [31:0] b_out,
//     output logic               out_vld,
//     output logic               out_sel_v  // Новый транзитный выходной сигнал
// );

//     // --- Stage 1: Просто гоним данные каждый такт ---
//     logic signed [31:0] x_reg, y_reg, b_reg;
//     logic               sel_reg, sub_reg;
//     logic               vld_pipe1;
//     logic               sel_out_pipe1; // Регистр первого такта для нового сигнала

//     always_ff @(posedge clk) begin
//         if (!rst_n) begin
//             vld_pipe1     <= 1'b0; // Сбрасываем только валидность
//             sel_out_pipe1 <= 1'b0; // И новый транзитный сигнал управления
//         end else begin
//             vld_pipe1     <= in_vld;
//             sel_out_pipe1 <= sel_out_v;
//         end
        
//         // Данные просто летят, плевать валидны они или нет
//         x_reg   <= x;
//         y_reg   <= y;
//         b_reg   <= b;
//         sel_reg <= sel;
//         sub_reg <= sub;
//     end

//     // --- Математика (чистый SystemVerilog без ручного расширения знака) ---
//     logic signed [32:0] sum_ext;
//     logic signed [31:0] saturated;

//     assign sum_ext = sub_reg ? (33'(x_reg) - 33'(y_reg)) : (33'(x_reg) + 33'(y_reg));

//     always_comb begin
//         if (sum_ext[32] != sum_ext[31]) begin
//             saturated = sum_ext[32] ? 32'sh8000_0000 : 32'sh7FFF_FFFF;
//         end else begin
//             saturated = sum_ext[31:0];
//         end
//     end

//     // --- Stage 2: Выходной сдвиг ---
//     always_ff @(posedge clk) begin
//         if (!rst_n) begin
//             out_vld   <= 1'b0;
//             out_sel_v <= 1'b0; // Сброс выходного транзитного сигнала
//         end else begin
//             out_vld   <= vld_pipe1;
//             out_sel_v <= sel_out_pipe1; // Передача на выход модуля
//         end

//         // Никакого маскирования нулями. Кто-то в конце разберется по out_vld
//         a_out <= sel_reg ? saturated : x_reg;
//         b_out <= b_reg;
//     end

// endmodule








































































// module pe_input_mux (
//     input  logic               clk,
//     input  logic               rst_n,
//     input  logic               in_vld,
//     input  logic signed [31:0] x,
//     input  logic signed [31:0] y,
//     input  logic signed [31:0] b,
//     input  logic               sel,
//     input  logic               sub,

//     output logic signed [31:0] a_out,
//     output logic signed [31:0] b_out,
//     output logic               out_vld
// );

//     // --- Stage 1: Просто гоним данные каждый такт ---
//     logic signed [31:0] x_reg, y_reg, b_reg;
//     logic               sel_reg, sub_reg;
//     logic               vld_pipe1;

//     always_ff @(posedge clk) begin
//         if (!rst_n) begin
//             vld_pipe1 <= 1'b0; // Сбрасываем только валидность
//         end else begin
//             vld_pipe1 <= in_vld;
//         end
        
//         // Данные просто летят, плевать валидны они или нет
//         x_reg   <= x;
//         y_reg   <= y;
//         b_reg   <= b;
//         sel_reg <= sel;
//         sub_reg <= sub;
//     end

//     // --- Математика (чистый SystemVerilog без ручного расширения знака) ---
//     logic signed [32:0] sum_ext;
//     logic signed [31:0] saturated;

//     assign sum_ext = sub_reg ? (33'(x_reg) - 33'(y_reg)) : (33'(x_reg) + 33'(y_reg));

//     always_comb begin
//         if (sum_ext[32] != sum_ext[31]) begin
//             saturated = sum_ext[32] ? 32'sh8000_0000 : 32'sh7FFF_FFFF;
//         end else begin
//             saturated = sum_ext[31:0];
//         end
//     end

//     // --- Stage 2: Выходной сдвиг ---
//     always_ff @(posedge clk) begin
//         if (!rst_n) begin
//             out_vld <= 1'b0;
//         end else begin
//             out_vld <= vld_pipe1;
//         end

//         // Никакого маскирования нулями. Кто-то в конце разберется по out_vld
//         a_out <= sel_reg ? saturated : x_reg;
//         b_out <= b_reg;
//     end

// endmodule
