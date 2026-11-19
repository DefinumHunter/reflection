module interface_test_pe (
    data_if.sink upstream,
    data_if.source downstream
);
    assign downstream.data = upstream.data;
    assign downstream.valid = upstream.valid;
endmodule
