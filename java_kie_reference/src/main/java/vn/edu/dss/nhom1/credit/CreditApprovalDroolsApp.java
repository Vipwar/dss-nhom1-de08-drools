package vn.edu.dss.nhom1.credit;

import org.kie.api.KieServices;
import org.kie.api.event.rule.AfterMatchFiredEvent;
import org.kie.api.event.rule.DefaultAgendaEventListener;
import org.kie.api.runtime.KieContainer;
import org.kie.api.runtime.KieSession;
import vn.edu.dss.nhom1.credit.model.Applicant;

/**
 * Minh hoa kien truc khoi tao KieServices -> KieContainer -> KieSession tren Java KIE
 * thuc thi cung pipeline 4 tang agenda-group cua file rules/credit_approval.drl.
 */
public class CreditApprovalDroolsApp {

    public static void main(String[] args) {
        KieServices ks = KieServices.Factory.get();
        KieContainer kContainer = ks.getKieClasspathContainer();
        KieSession kSession = kContainer.newKieSession("CreditApprovalKSession");

        // Gan AgendaEventListener de truy vet chuoi luat kich hoat
        kSession.addEventListener(new DefaultAgendaEventListener() {
            @Override
            public void afterMatchFired(AfterMatchFiredEvent event) {
                System.out.println("[Drools KIE Fired] Rule: " + event.getMatch().getRule().getName());
            }
        });

        // Day thu tu 4 tang agenda-group vao Focus Stack (LIFO)
        kSession.getAgenda().getAgendaGroup("4-dss-explanation").setFocus();
        kSession.getAgenda().getAgendaGroup("3-pricing-decision").setFocus();
        kSession.getAgenda().getAgendaGroup("2-risk-scoring").setFocus();
        kSession.getAgenda().getAgendaGroup("1-eligibility").setFocus();

        // Chay Suy dien tien (Forward Chaining)
        int firedCount = kSession.fireAllRules();
        System.out.println("Tong so chu ky luat kich hoat: " + firedCount);
        kSession.dispose();
    }
}
