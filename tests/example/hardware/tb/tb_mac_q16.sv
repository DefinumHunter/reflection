`timescale 1ns/1ps

`timescale 1ns/1ps

module tb_mac_q16;
    parameter int PIPELINE_STAGES = 4;

    logic        clk;
    logic        rst_n;
    logic signed [31:0] in_a, in_b;
    logic               in_vld;
    logic               sel;        // Добавленный входной сигнал для dut
    logic               busy;
    logic               out_vld;
    logic               out_sel;    // Добавленный выходной сигнал из dut
    logic signed [31:0] out_res;
    logic        [3:0]  in_id;
    logic        [3:0]  out_id;

    mac_q16 #(
        .PIPELINE_STAGES(PIPELINE_STAGES)
    ) dut (.*);

    initial begin
        $dumpfile("waves.vcd");
        $dumpvars(0, tb_mac_q16);
    end
endmodule




















































// module tb_mac_q16;
//     parameter int PIPELINE_STAGES = 4;

//     logic        clk;
//     logic        rst_n;
//     logic signed [31:0] in_a, in_b;
//     logic               in_vld;
//     logic               busy;
//     logic               out_vld;
//     logic signed [31:0] out_res;

//     mac_q16 #(
//         .PIPELINE_STAGES(PIPELINE_STAGES)
//     ) dut (.*);

//     initial begin
//         $dumpfile("waves.vcd");
//         $dumpvars(0, tb_mac_q16);
//     end
// endmodule




















// `timescale 1ns/1ps

// module mac_q16_tb;

//     // ── Parameters ───────────────────────────────────────────────
//     parameter int PIPELINE_STAGES = 3;
//     parameter int CLK_PERIOD      = 10;
//     parameter int N_VECTORS       = 215; // должно совпадать с Python

//     // ── Signals ──────────────────────────────────────────────────
//     logic        clk   = 0;
//     logic        rst_n = 0;
//     //logic signed [31:0] in_a, in_b, in_c;
//     //logic signed [31:0] in_a=0, in_b=0, in_c=0; // Явное обнуление при старте
//     logic signed [31:0] in_a, in_b, in_c; // Явное обнуление при старте
//     logic               in_vld;
//     logic               busy;     // Тот самый сигнал "я работаю"
//     logic               out_vld;
//     logic signed [31:0] out_res;

//     // ── DUT ──────────────────────────────────────────────────────
//     mac_q16 #(
//         .PIPELINE_STAGES(PIPELINE_STAGES)
//     ) dut (.*);

//     // ── Clock ────────────────────────────────────────────────────
//     always #(CLK_PERIOD/2) clk = ~clk;

//     // ── Stimulus and results storage ─────────────────────────────
//     logic [31:0] stimulus [0 : N_VECTORS*3-1];
//     logic [31:0] results  [0 : N_VECTORS-1];

//     // At the top
//     real gap_prob = 0.2;
//     int  gap_cycles;

//     // ── Main ─────────────────────────────────────────────────────
//     initial begin
//         // Load stimulus
//         //$readmemh("../../sim/vectors/mac_q16_in.mem", stimulus);
//         $readmemh("D:/FPGA/Diplom_Verefication/sim/vectors/mac_q16_in.mem", stimulus);


//         // 1. Сброс
//         rst_n = 0; in_a = 0; in_b = 0; in_c = 0;
//         repeat(5) @(posedge clk);
//         rst_n = 1; repeat(5) @(posedge clk);

//         // 2. Цикл: шлем и тут же планируем забор данных
//         for (int i = 0; i < N_VECTORS; i++) begin
//             // Шлем данные
//             //@(posedge clk);
//             in_a = stimulus[i*3 + 0];
//             in_b = stimulus[i*3 + 1];
//             in_c = stimulus[i*3 + 2];
//             #1
//             in_vld = 1;//
//             @(posedge clk);
//             // СРАЗУ планируем, что через N тактов мы заберем ответ для ЭТОГО вектора
//             fork
//                 automatic int idx = i; // Запоминаем текущий индекс
//                 begin
//                     repeat(PIPELINE_STAGES) @(posedge clk); 
//                     //@(posedge clk iff (out_vld === 1));
//                     //#1; // Чуть-чуть отступаем от фронта, чтобы данные успели обновиться
//                     results[idx] = out_res;
//                 end
//             join_none

//              // 
//             //@(posedge clk); // Ждем такт, чтобы подать следующий вектор
//             in_vld = 0; // 

//             // Random idle gap
//             if ($urandom_range(0,99) < 20) begin
//                 gap_cycles = $urandom_range(1, 3);
//                 repeat(gap_cycles) @(posedge clk);
//             end

//         end

//         // 3. Ждем, пока последний fork доработает
//         repeat(PIPELINE_STAGES + 1) @(posedge clk);
        
//         // Всё, массив results заполнен идеально по индексам
//     //end







//         // Write results
//         //$writememh("../../sim/results/mac_q16_out.mem", results);
//         $writememh("D:/FPGA/Diplom_Verefication/sim/results/mac_q16_out.mem", results);

//         $display("TB done — %0d vectors written", N_VECTORS);
//         $finish;
//     end

    // ── Capture outputs ──────────────────────────────────────────
    // initial begin
    //     // Wait for reset + 1 cycle for first result
    //     repeat(7 + PIPELINE_STAGES) @(posedge clk);

    //     for (int i = 0; i < N_VECTORS; i++) begin
    //         results[i] = out_res;
    //         @(posedge clk);
    //     end
    // end
    // ── Capture outputs ──────────────────────────────────────────
    // int capture_idx = 0;
    // logic capturing = 0;

    // // Start capturing after reset + idle + pipeline delay
    // initial begin
    //     repeat(5 + 2 + PIPELINE_STAGES) @(posedge clk);
    //     capturing = 1;
    // end

    // always_ff @(posedge clk) begin
    //     if (capturing && capture_idx < N_VECTORS) begin
    //         results[capture_idx] <= out_res;
    //         capture_idx++;
    //     end
    // end

    // Capture outputs
    // initial begin
    //     // Wait for reset (5 cycles) + release (2 cycles) + pipeline + 1 extra cycle
    //     repeat(5 + 2 + PIPELINE_STAGES + 1) @(posedge clk);

    //     for (int i = 0; i < N_VECTORS; i++) begin
    //         results[i] = out_res;
    //         @(posedge clk);
    //     end
    // end

// endmodule
