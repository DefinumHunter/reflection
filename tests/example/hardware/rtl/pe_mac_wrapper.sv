`timescale 1ns / 1ps

//////////////////////////////////////////////////////////////////////////////////
// Wrapper: pe_input_mux -> mac_q16
// Транзакция задаётся issue_vld (+ issue_sel, id): mux выдаёт её через 1 такт,
// mac — ещё через PIPELINE_STAGES. out_res, out_vld, out_sel, out_id выходят
// вместе, через 1 + PIPELINE_STAGES тактов после issue_vld.
// Данные в mux загружаются заранее (sel), минимум за такт до issue_vld.
//////////////////////////////////////////////////////////////////////////////////

module pe_mac_wrapper #(
    parameter int PIPELINE_STAGES = 4
) (
    // ===== Системные сигналы =====
    input  logic               clk,
    input  logic               rst_n,

    // ===== Входы для pe_input_mux =====
    input  logic signed [31:0] local_data,
    input  logic               sub,
    input  logic signed [31:0] in_a,
    input  logic signed [31:0] in_b,
    input  logic        [1:0]  sel,         // Выбор режима мультиплексора (2 бита)
    input  logic        [3:0]  in_id,
    input  logic               issue_vld,   // Выдача транзакции из mux в mac
    input  logic               mac_sel_in,  // Команда для MAC, подаётся вместе с issue_vld

    // ===== Выходы mac_q16 =====
    output logic               out_vld,     // Валидный результат на выходе MAC
    output logic               out_sel,     // Команда, выровненная с результатом
    output logic signed [31:0] out_res,     // Результат вычислений MAC
    output logic        [3:0]  out_id,      // ID, выровненный с результатом
    output logic               busy         // Флаг занятости MAC
);

    // =============================================
    // Внутренние шины связи между MUX и MAC
    // =============================================
    logic               mux_out_vld;
    logic               mux_out_sel;
    logic signed [31:0] mux_a_out;
    logic signed [31:0] mux_b_out;
    logic        [3:0]  mux_out_id;

    pe_input_mux u_mux (
        .clk        (clk),
        .rst_n      (rst_n),
        .local_data (local_data),
        .sub        (sub),
        .in_a       (in_a),
        .in_b       (in_b),
        .sel        (sel),
        .in_id      (in_id),
        .issue_vld  (issue_vld),
        .issue_sel  (mac_sel_in),

        .a_out      (mux_a_out),
        .b_out      (mux_b_out),
        .out_id     (mux_out_id),
        .out_vld    (mux_out_vld),
        .out_sel    (mux_out_sel)
    );

    mac_q16 #(
        .PIPELINE_STAGES(PIPELINE_STAGES)
    ) u_mac (
        .clk    (clk),
        .rst_n  (rst_n),
        .in_vld (mux_out_vld),
        .sel    (mux_out_sel),
        .in_a   (mux_a_out),
        .in_b   (mux_b_out),
        .in_id  (mux_out_id),

        .out_vld(out_vld),
        .out_sel(out_sel),
        .out_res(out_res),
        .out_id (out_id),
        .busy   (busy)
    );

endmodule
