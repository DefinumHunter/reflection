interface handshake_if;
    logic [15:0] data;
    logic valid;
    logic ready;
    modport consumer (input data, valid, output ready);
    modport producer (output data, valid, input ready);
endinterface

module handshake_stage (
    handshake_if.consumer upstream,
    handshake_if.producer downstream
);
    assign downstream.data = upstream.data;
    assign downstream.valid = upstream.valid;
    assign upstream.ready = downstream.ready;
endmodule

module handshake_top;
    handshake_if first();
    handshake_if middle();
    handshake_if last();

    handshake_stage stage0(.upstream(first), .downstream(middle));
    handshake_stage stage1(.upstream(middle), .downstream(last));
endmodule

module handshake_bad_top;
    handshake_if shared();
    handshake_if in0();
    handshake_if in1();

    // Two producer outputs intentionally drive the same interface.
    handshake_stage stage0(.upstream(in0), .downstream(shared));
    handshake_stage stage1(.upstream(in1), .downstream(shared));
endmodule
