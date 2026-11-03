module winnower #(
    parameter int NUM_SLOTS = 9,
    parameter int GROUPS    = 3
)(
    input  logic clk,
    input  logic rst_n,

    // ---- От array_output_router: обычный (array) путь, valid уже погашен
    //      апстримом для CORDIC-групп, но сам id ещё не обнулён ----
    input  logic signed [31:0] win_data  [0:NUM_SLOTS-1],
    input  logic         [3:0] win_id    [0:NUM_SLOTS-1],
    input  logic               win_valid [0:NUM_SLOTS-1],

    // ---- От array_output_router: путь CORDIC, один результат на группу ----
    input  logic signed [31:0] cordic_data  [0:GROUPS-1],
    input  logic         [3:0] cordic_id    [0:GROUPS-1],
    input  logic               cordic_valid [0:GROUPS-1],

    // ---- Итоговый пакет: id=0000 = "эта линия пуста", ID 1..9 = реальные данные ----
    output logic signed [31:0] out_data [0:NUM_SLOTS-1],
    output logic         [3:0] out_id   [0:NUM_SLOTS-1],
    output logic         [31:0] crc32,
    output logic                out_valid   // просто OR всех строк, для удобства приёмника
);

    localparam int SLOTS_PER_GROUP = NUM_SLOTS / GROUPS;

    // ---- Комбинационная сборка 9 слотов: CORDIC занимает только первую
    //      позицию своей группы (см. договорённость — "вариант А"), сентинел id=0 ----
    logic signed [31:0] slot_data_comb [0:NUM_SLOTS-1];
    logic         [3:0] slot_id_comb   [0:NUM_SLOTS-1];

    genvar g;
    generate
        for (g = 0; g < GROUPS; g++) begin : combine_group
            localparam int HOME = g * SLOTS_PER_GROUP; // первая позиция группы

            // Первая позиция: CORDIC, если валиден, иначе обычный array-путь.
            // win_id/cordic_id уже надёжно 0000 при невалидности — гейтинг сделан
            // в array_output_router, здесь достаточно просто выбрать источник.
            assign slot_data_comb[HOME] = cordic_valid[g] ? cordic_data[g]
                                                            : win_data[HOME];
            assign slot_id_comb[HOME]   = cordic_valid[g] ? cordic_id[g] : win_id[HOME];

            // Остальные 2 позиции группы: только обычный array-путь.
            for (genvar s = 1; s < SLOTS_PER_GROUP; s++) begin : rest_slots
                localparam int SLOT = HOME + s;
                assign slot_data_comb[SLOT] = win_data[SLOT];
                assign slot_id_comb[SLOT]   = win_id[SLOT];
            end
        end
    endgenerate

    // ---- Упаковка payload для CRC: {id[3:0], data[31:0]} на слот, 9 слотов = 324 бита ----
    localparam int SLOT_W    = 36;
    localparam int PAYLOAD_W = NUM_SLOTS * SLOT_W;

    logic [PAYLOAD_W-1:0] payload_comb;
    generate
        for (g = 0; g < NUM_SLOTS; g++) begin : pack_payload
            assign payload_comb[g*SLOT_W +: SLOT_W] = {slot_id_comb[g], slot_data_comb[g]};
        end
    endgenerate

    // ---- CRC-32 (полином 0x04C11DB7, стандартный), развёрнутый по всем 324 битам ----
    // Комбинационный XOR-массив на всю ширину payload — если не уложится по таймингу
    // на синтезе, это первый кандидат на отдельную регистровую стадию/распараллеливание.
    function automatic logic [31:0] crc32_calc(input logic [PAYLOAD_W-1:0] data);
        logic [31:0] crc;
        crc = 32'hFFFFFFFF;
        for (int i = 0; i < PAYLOAD_W; i++) begin
            logic bit_in;
            logic msb;
            bit_in = data[i];
            msb    = crc[31] ^ bit_in;
            crc    = {crc[30:0], 1'b0};
            if (msb) crc = crc ^ 32'h04C11DB7;
        end
        return crc;
    endfunction

    logic [31:0] crc_comb;
    assign crc_comb = crc32_calc(payload_comb);

    logic slot_any_valid_comb;
    assign slot_any_valid_comb = |{cordic_valid[0], cordic_valid[1], cordic_valid[2],
                                    win_valid[0], win_valid[1], win_valid[2],
                                    win_valid[3], win_valid[4], win_valid[5],
                                    win_valid[6], win_valid[7], win_valid[8]};

    // ---- Регистр на выходе: одна стадия, данные и CRC защёлкиваются синхронно ----
    always_ff @(posedge clk) begin
        if (!rst_n) begin
            for (int i = 0; i < NUM_SLOTS; i++) begin
                out_data[i] <= '0;
                out_id[i]   <= 4'b0000;
            end
            crc32     <= '0;
            out_valid <= 1'b0;
        end else begin
            for (int i = 0; i < NUM_SLOTS; i++) begin
                out_data[i] <= slot_data_comb[i];
                out_id[i]   <= slot_id_comb[i];
            end
            crc32     <= crc_comb;
            out_valid <= slot_any_valid_comb;
        end
    end

endmodule
