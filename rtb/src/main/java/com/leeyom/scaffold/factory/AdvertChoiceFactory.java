package com.leeyom.scaffold.factory;

import com.leeyom.scaffold.enums.AdvChoiceStrategyEnum;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.Map;

@Component
public class AdvertChoiceFactory {

    @Autowired
    private Map<String, IAdvertChoice> advertChoiceMap;

    public IAdvertChoice getInstance(AdvChoiceStrategyEnum advChoiceStrategyEnum) {
        IAdvertChoice instance = advertChoiceMap.get(advChoiceStrategyEnum.getValue());
        return instance;
    }


}
