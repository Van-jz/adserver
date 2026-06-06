package com.leeyom.scaffold.factory;

import com.leeyom.scaffold.enums.AdvChoiceStrategyEnum;

import java.util.List;

public interface IAdvertChoice {

    AdvChoiceStrategyEnum getCode();

    Advert choose(List<Advert> waitChooseAdvertList, UserBO userBO);
}
