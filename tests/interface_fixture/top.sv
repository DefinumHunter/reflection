`timescale 1ns/1ps

module interface_test_top;
    data_if in0();
    data_if in1();
    data_if shared();
    data_if mid();
    data_if out0();
    data_if out1();
    data_if out2();
    data_if out3();
    data_if out4();

    interface_test_pe pe0(.upstream(in0),    .downstream(mid));
    interface_test_pe pe1(.upstream(mid),    .downstream(out1));
    interface_test_pe pe2(.upstream(in1),    .downstream(out2));
    interface_test_pe pe3(.upstream(shared), .downstream(out3));
    interface_test_pe pe4(.upstream(shared), .downstream(out4));
endmodule
