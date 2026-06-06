package com.leeyom.scaffold.dto.resp;

import lombok.Data;

import java.util.List;

@Data
public class BidResp {
    private String id; // = request.id
    private String bidid; //响应唯一id
    private String cur;
    private List<Seatbid> seatbid;
    private Integer nbr = 1000; // 不参与竞价的原因，1000是太贵了
    private BidRespExt ext;

}
