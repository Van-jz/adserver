package com.leeyom.scaffold.service;

import com.leeyom.scaffold.dto.req.BidRequest;
import com.leeyom.scaffold.dto.resp.BidResp;

public interface SspService {
    BidResp req(BidRequest bidRequest);
}
