package com.leeyom.scaffold.dto.resp;

import lombok.Data;

import java.util.List;

@Data
public class Seatbid {

    private String seat;

    private List<Bid> bid;
}
