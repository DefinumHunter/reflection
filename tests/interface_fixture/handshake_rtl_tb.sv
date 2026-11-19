`timescale 1ns/1ps

module handshake_rtl_tb;
    handshake_if source_bus();
    handshake_if sink_bus();

    handshake_stage dut (
        .upstream(source_bus),
        .downstream(sink_bus)
    );

    task automatic check(
        input logic [15:0] data,
        input logic valid,
        input logic ready
    );
        source_bus.data = data;
        source_bus.valid = valid;
        sink_bus.ready = ready;

        #1;

        assert (sink_bus.data === data)
            else $fatal(1, "data mismatch");
        assert (sink_bus.valid === valid)
            else $fatal(1, "valid mismatch");
        assert (source_bus.ready === ready)
            else $fatal(1, "ready mismatch");
    endtask

    initial begin
        check(16'h1234, 1'b1, 1'b0);
        check(16'hABCD, 1'b0, 1'b1);
        check(16'h0000, 1'b1, 1'b1);

        $display("HANDSHAKE RTL PASS: 3 vectors");
        $finish;
    end
endmodule
